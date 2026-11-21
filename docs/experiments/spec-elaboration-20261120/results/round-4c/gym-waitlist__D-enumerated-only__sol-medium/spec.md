## Use cases

### U-1: A member joins a full class's waitlist to get a chance at a seat
Flow: The member opens a bookable class occurrence with zero available spots. They choose the waitlist action and see that they are waiting. If the waitlist is empty, they become its first entry. If there are already entries, including a long queue, the eligible member can still join. On a later visit, they see their own status. Repeating the join shows the existing entry. If a direct seat opens before they can join, the app gives them the ordinary booking action.
Source: request

### U-2: A member leaves a waitlist to stop waiting for a seat
Flow: The member opens their active entry and chooses to leave. They see that they are no longer waiting. If a seat was already offered, leaving also gives up the offer. If the member already has a confirmed booking from the waitlist, the app directs them to the ordinary booking cancellation flow.
Source: implied: a member who joined while the class was full can change their plans

### U-3: A waitlisted member claims an opening to attend the class
Flow: An ordinary booking cancellation or other opening frees a spot. The member sees an in-app offer with a deadline. They accept using the existing booking terms and see a confirmed booking. If they pass, let the deadline expire, or no longer qualify, the next eligible member can get the spot. If a required booking step fails, the member can retry while the offer remains valid. With no eligible waiters, an unheld spot is available through ordinary booking.
Source: implied: the waitlist gives people a way into a class that was full

### U-4: A member handles a refused or uncertain action to learn where they stand
Flow: The member tries a waitlist action against a missing, unavailable, or unauthorized occurrence, an expired offer, or an entry that has changed. The app reports the current result where the member is authorized to see it. If the result is uncertain after an outage, the member can reopen the occurrence or repeat the action to find their current state.
Source: implied: a full class is only one reason an attempted booking can fail

### U-5: A member books an open class to reserve a spot directly
Flow: The member opens an occurrence with a spot available to the public and uses ordinary booking. If the last spot disappears before booking finishes, the member can choose the waitlist when eligible. They can still see or cancel a confirmed reservation through the ordinary booking flow.
Source: implied: “Add a waitlist to our class booking app” extends the existing booking flow

### U-6: An operator changes the rollout setting to start or stop waitlist service
Flow: An authorized operator enables the waitlist for the booking app. Existing scheduled occurrences and bookings still work. The operator can stop the waitlist and check that open entries have ended. If members later regain access to the waitlist, they choose to join again. If saving the setting fails, the operator checks the effective setting before acting again. To return to the older app version, the operator disables the feature and verifies that outstanding entries are closed before switching versions.
Source: implied: adding the feature to an existing app requires rollout and a way to stop it

### U-7: An operator manages a class occurrence to keep availability accurate
Flow: An authorized operator uses the existing class controls available to them. When bookable capacity opens, the queue gets access to it. When a permitted capacity reduction displaces an offer, the operator can see which offers remain active. If the occurrence closes, starts, or is canceled, the operator sees that waiting and offers have ended.
Source: implied: a waitlist depends on the occurrence and its bookable capacity

### U-8: An operator inspects waitlist service to diagnose and recover from disruption
Flow: The operator opens a class's waitlist view and checks waiting entries, active offers, service status, and whether the queue is empty. If processing is unavailable, the operator sees that status. After service returns, they can check the resulting queue and bookings from current data.
Source: implied: the waitlist depends on availability changes that can fail or arrive late

## Clauses

### C-1: A member can join a waitlist for a full class occurrence.
Observable: Open a full class occurrence available to the member for booking and join its waitlist. The app confirms the member is waiting for that occurrence.
Source: request

### C-2: A waitlisted member can get a seat when one opens.
Observable: Join the waitlist for a full occurrence. When a seat opens before booking closes, follow the waitlist flow to obtain a confirmed booking for that occurrence.
Source: implied: U-3 and “so full classes don't turn people away”

### C-3: A member can view their own active waitlist status.
Observable: Leave the class screen after joining, then reopen the same occurrence with the same account. The app shows the member the current state of their own enrollment.
Source: implied: U-1

### C-4: A member can withdraw from an active waitlist entry.
Observable: Choose to leave while waiting for the occurrence. The entry no longer appears as active.
Source: implied: U-2

### C-5: An open seat can be booked through the ordinary booking flow.
Observable: Open a class occurrence with capacity available to ordinary booking. The existing booking action can still confirm a seat for an eligible member.
Source: implied: U-5

### C-6: An unauthorized member cannot join a class through its waitlist.
Observable: Using an account denied access to a class occurrence, submit a join for it. The member gains no waitlist entry.
Source: implied: U-4

### C-7: Authorized operators can enable waitlist enrollment for the app.
Observable: With the feature disabled, enable it as an operator. An eligible member can then join a full occurrence that is open for booking.
Source: choice: U-6 needs a rollout control and a single app-wide setting is sufficient

### C-8: Authorized operators can disable waitlist enrollment for the app.
Observable: Disable the feature and attempt to join a full occurrence from a member account. Joining is unavailable.
Source: choice: the rollout control must support stopping enrollment as well as starting it

### C-9: New availability can be used by the waitlist.
Observable: Release a confirmed reservation for a full occurrence that remains open. The waitlist can use the vacancy caused by releasing that reservation.
Source: implied: U-3

### C-10: Authorized operators can inspect the waitlist for a class occurrence.
Observable: Open an occurrence with active waitlist entries in the operator view. The operator can find that occurrence's queue.
Source: choice: U-8 requires a way to distinguish a working list from a reported issue

### C-11: Each separately bookable occurrence has its own waitlist.
Observable: Join one occurrence of a recurring class. The join creates no entry for another occurrence of that class.
Source: implied: U-1 books a particular class occurrence

### C-12: A class occurrence must resolve to an existing occurrence before a waitlist action can change it.
Observable: Submit a join, leave, or claim using a malformed, unknown, or deleted occurrence reference. The action fails without changing a waitlist or booking.
Source: implied: U-4 requires a real target

### C-13: Waitlist entries belong to the acting member's existing booking identity.
Observable: Open the same occurrence as the same member on a second device. A waitlist entry created on the first device belongs to that same member.
Source: implied: U-1 requires a member to find their entry again

### C-14: Waitlist actions require an authenticated member.
Observable: Attempt to join, leave, or claim while signed out. The app requires sign-in before the action can make any change.
Source: implied: U-4 and a waitlist entry must belong to its member

### C-15: A member can act only on their own waitlist entries.
Observable: As another signed-in member, submit a leave or claim using someone else's entry or offer reference. The owner's entry stays as it was.
Source: implied: U-2 and U-3 act on the member's own place

### C-16: The waitlist does not expand the audience allowed to discover an occurrence.
Observable: As an account unable to view an occurrence, try to open it through the waitlist surface or an offer reference. The app discloses no occurrence or waitlist details.
Source: implied: U-4 uses existing class access

### C-17: Full means zero seats are currently available for ordinary booking.
Observable: View an otherwise bookable occurrence with no public seat. Two examples are an occurrence with every seat confirmed and an occurrence whose last seat is held by a live offer. An eligible member without a booking or entry can join in either case.
Source: choice: held seats count as committed capacity while another member decides

### C-18: A member cannot join while a seat is available to ordinary booking.
Observable: Attempt a join on an otherwise bookable occurrence with at least 1 seat open to ordinary booking. The app presents ordinary booking and creates no entry.
Source: choice: immediate booking already meets the request when seats are open

### C-19: A member with a confirmed seat cannot join the waitlist for that occurrence.
Observable: Book a seat, then try to join the waitlist for the same occurrence once it is full. The app shows the existing booking and creates no entry.
Source: implied: U-1 seeks a seat the member does not have

### C-20: Joining requires the same member and occurrence eligibility as ordinary booking, apart from seat availability and steps that complete a booking.
Observable: Try joining a full occurrence with an account denied an ordinary booking for a reason besides capacity or an unfinished booking completion step. The app refuses the join. The deployed app supplies the eligibility rules, whose individual predicates are unconfirmed.
Source: choice: use existing class restrictions while deferring any required terms, payment authorization, or other booking completion steps until claim

### C-21: The waitlist closes at the earlier of the occurrence's existing booking cutoff and its scheduled start.
Observable: Attempt a join at the instant the earlier boundary is reached. The waitlist is closed. Where the app has no earlier booking cutoff, use the scheduled start. The existing cutoff offset, if any, is unconfirmed.
Source: choice: only offer seats while a booking can still be used

### C-22: An occurrence that is not open for ordinary booking for an occurrence-wide reason besides capacity has no open waitlist.
Observable: Try joining before bookings open, after bookings close, or after cancellation. For any further occurrence-wide booking restriction in the deployed app, try joining while that restriction is active. No entry is created. The further restrictions, if any, are unconfirmed.
Source: choice: the waitlist addresses capacity and inherits the deployed occurrence restrictions

### C-23: An active entry has exactly one status, waiting or offered.
Observable: View an active entry before seat assignment and during a live offer. It has the waiting status in the first case and the offered status in the second.
Source: choice: explicit offers let members choose whether to commit

### C-24: A closed entry has one outcome from withdrawn, expired, confirmed, ineligible, occurrence closed, or waitlist disabled.
Observable: Inspect each outcome in turn when closing an entry. Leave or decline produces withdrawn. A missed offer deadline produces expired while the occurrence and the feature remain open. The other outcomes correspond to confirmed booking, ineligibility, occurrence closure, and feature disablement.
Source: choice: these outcomes cover the specified lifecycle without adding a separate opt-out or no-show policy

### C-25: A member with an active entry cannot obtain a second active entry for the same occurrence.
Observable: Submit join twice for the same member and occurrence, including concurrently. Both resolve to the same active entry if it is still active. The second join does not change its turn.
Source: choice: a repeat submission must not change a member's chance of a seat

### C-26: Closing an entry ends the member's old turn in the queue.
Observable: Leave or let an offer expire, then join again if the occurrence still allows joining. The new entry gets a new turn behind existing waiting members.
Source: choice: leaving or missing a deadline releases priority as well as any seat

### C-27: Waitlist enrollment has no separate product queue-length limit.
Observable: Keep joining a full occurrence with distinct eligible members as the queue grows. A join is not refused solely for reaching a waitlist-specific count. The deployed runtime's supported storage and operating scale are unconfirmed.
Source: choice: an additional cap would turn away members the waitlist could serve

### C-28: The ordinary capacity configured for the occurrence remains its seat limit.
Observable: View a full occurrence and add waiters. The number of seats remains the operator-configured maximum for that occurrence. Supported capacity values and ranges are unconfirmed and follow the existing app.
Source: implied: U-1 adds a list to a full class without enlarging it

### C-29: Offers are ordered by when active entries successfully joined that occurrence.
Observable: Join as two members in sequence, then open one seat. The earlier still-eligible waiting member is offered it first. A join that fails before creating an entry gets no turn.
Source: choice: first come first served gives members a predictable turn

### C-30: Simultaneous joins have a stable relative order.
Observable: Submit two joins at the same time. Observe their relative order across repeats and assignments. Either initial order is acceptable, provided it stays consistent for those entries.
Source: choice: ties need consistent handling without a prescribed tie-break implementation

### C-31: An offer holds exactly 1 seat for its recipient.
Observable: With 1 free seat and a live offer, try to book the seat as another member. The held seat remains available only to the recipient through their claim.
Source: choice: a live offer needs a seat the recipient can actually claim

### C-32: A single entry has at most 1 active offer.
Observable: Free 2 seats while only 1 eligible member is waiting. That member gets 1 active offer.
Source: choice: each entry seeks one seat

### C-33: The offer deadline is 15 elapsed minutes after issuance or the occurrence's waitlist closing time, whichever comes first.
Observable: With closing time more than 15 minutes away, see a deadline 15 minutes after issuance. Repeat with 5 minutes to close and see a deadline 5 minutes after issuance.
Source: choice: a short fixed window gives members time to respond while letting the next member have a turn

### C-34: An offer is too late to claim at or after its deadline.
Observable: Attempt to confirm the offer 1 second before its deadline and at the deadline in otherwise identical cases. The earlier attempt can succeed if confirmation completes in time. At the deadline it cannot.
Source: choice: a single inclusive expiration boundary prevents a seat from having two claimants

### C-35: An in-app offer tells its recipient which occurrence it applies to.
Observable: Receive an offer and identify the existing class name and scheduled date and time for the offered occurrence. Identical display names are distinguished using the app's existing occurrence details.
Source: choice: the recipient needs to know what they are agreeing to attend

### C-36: An in-app offer shows its claim deadline.
Observable: Open an active offer and determine the instant by which a booking must be confirmed. The app uses its existing time display convention and supplies enough information to disambiguate the deadline.
Source: choice: the member needs to know when the opportunity ends

### C-37: The recipient can give up an offer without booking.
Observable: While an offer is active, decline it or leave the waitlist. The entry closes as withdrawn.
Source: choice: declining promptly gives someone else a chance

### C-38: An offer has a member-visible path to claim one seat.
Observable: Open a live offer and start the claim from it using the same member account. The path leads through the applicable booking completion steps.
Source: choice: affirmative acceptance avoids surprises for attendance and charges

### C-39: The app has one rollout setting affecting all occurrences in the same booking app.
Observable: Inspect the feature setting for two classes. Changing it affects both. No per-class overrides are required.
Source: choice: one setting provides rollout control without a second layer of configuration

### C-40: Only operators granted feature administration can change the rollout setting.
Observable: Attempt to change the setting as a member or an operator without feature administration access. The effective setting stays the same. The deployed app's role names are unconfirmed.
Source: choice: use the app's operator authorization for rollout

### C-41: Only operators granted class management for an occurrence can inspect its waitlist.
Observable: As an operator without management access to an occurrence, try to open its waitlist. The view discloses no entries.
Source: choice: class operators need only the queues they manage

### C-42: An eligible waiting member has priority over a new ordinary booking for an opening in the same occurrence.
Observable: After a cancellation frees 1 seat for an eligible waiter, race an ordinary booking against offer assignment. The ordinary booking cannot take that seat.
Source: choice: new arrivals cannot bypass people already waiting

### C-43: An opening from an increase in bookable capacity is eligible for offer assignment.
Observable: Increase capacity by 1 on a full open occurrence with an eligible waiter. That member gets the new opening through the waitlist.
Source: choice: an additional bookable seat serves the same purpose as a canceled booking

### C-44: Assignment uses all available seats for which there are eligible waiting members.
Observable: Free 3 seats while 2 eligible members are waiting. Both members are offered a seat. Once those seats are held, the third seat can be booked directly.
Source: choice: assign each opening to a different eligible waiter without keeping excess seats idle

### C-45: An offer release makes its seat eligible for assignment again while the waitlist remains open.
Observable: With 2 waiters for 1 seat, decline, withdraw, or let the earlier member's offer expire in separate scenarios. The next eligible waiting member can get an offer for the seat.
Source: choice: a member who passes should not end the opportunity for the queue

### C-46: A free seat can return to ordinary booking when it has no eligible waiting member to serve.
Observable: Let the last live offer expire while the occurrence remains open and no eligible members are waiting. An eligible member can book the released seat directly.
Source: choice: a seat serves the waitlist only while someone can use it

### C-47: An entry found ineligible during assignment closes as ineligible.
Observable: Change the first waiter's eligibility before freeing a seat. That entry closes and does not take a turn ahead of any eligible waiter.
Source: choice: the waitlist must respect current booking restrictions without blocking other members

### C-48: A claim checks the recipient's current booking eligibility.
Observable: Give a member an offer, then make that member ineligible before they submit a claim. The claim is refused and the entry closes as ineligible. The ineligibility conditions are the same ones used for join, with completion requirements applied at claim under the existing booking flow.
Source: choice: a prior offer does not waive current booking restrictions

### C-49: Successful claim confirmation consumes its seat hold.
Observable: Confirm a claim for the last held seat. In subsequent reads the seat counts as a confirmed booking once, with no live offer still holding capacity for it.
Source: choice: confirmation replaces the offer with the ordinary reservation

### C-50: A failed booking completion can be retried on the same live offer.
Observable: Decline required terms, abandon checkout, or have payment authorization fail, where those steps apply. If the offer remains live and the member is still eligible, reopen it and attempt to claim again.
Source: choice: a recoverable completion failure does not forfeit the recipient's remaining time

### C-51: An attempted claim that fails to create a booking does not complete the entry as confirmed.
Observable: Cause a required booking step or the booking service to fail. Reopen the occurrence and see the actual entry status with no confirmed booking from that attempt.
Source: implied: U-3 gets a seat only if a booking exists

### C-52: A repeated claim of an already confirmed offer resolves to its original booking outcome.
Observable: Confirm an offer, lose the response, then resubmit the same claim. While the original result is still accessible to the member, the app identifies the original booking and indicates its current status, even if it has since been canceled. The retry cannot buy or reserve a new seat.
Source: choice: an uncertain confirmation result can be recovered without a second booking

### C-53: A repeated leave applies only to the entry it originally targeted.
Observable: Leave, rejoin on a new explicit action, then repeat the old leave. The app reports that the target entry is closed and keeps the new entry active.
Source: choice: retries must not accidentally withdraw a later queue entry

### C-54: A claim applies only to the offer it originally targeted.
Observable: Lose an offer, get a later offer, and resubmit the earlier claim. The app reports the earlier offer is no longer valid and the later offer is still claimable.
Source: choice: the recipient must act on the current offer and deadline

### C-55: A retried successful join does not recreate its entry after closure.
Observable: Join, close the entry, then retry the original submission after a connection interruption. It resolves to the original entry or its closed result. A fresh explicit join is needed for a new turn.
Source: choice: replaying a request does not undo a later decision

### C-56: Concurrent withdrawal and claim of one entry resolve to a single terminal outcome.
Observable: Submit a leave and a valid claim simultaneously. If leave wins there is no booking from the offer. If claim wins there is one confirmed booking, which remains subject to ordinary cancellation.
Source: choice: the member's entry cannot be both withdrawn and confirmed

### C-57: An expired offer stops holding capacity at its deadline.
Observable: Keep the client open without refreshing, then wait past the deadline and try the claim. Reopening sees no live hold for that offer even if background processing was delayed.
Source: choice: delayed delivery or processing cannot extend the exclusive claim window

### C-58: A canceled occurrence closes the waitlist.
Observable: Cancel an occurrence with waiting members and offered members. All active entries end as occurrence closed.
Source: choice: there is no seat to offer for a canceled class

### C-59: The waitlist ends when the occurrence reaches its waitlist closing time.
Observable: Reach the closing time with waiting members and outstanding offers. Active entries end as occurrence closed.
Source: choice: pending entries need a terminal result when new reservations become too late

### C-60: A newly effective occurrence-wide booking restriction ends open entries while the class is unavailable.
Observable: Apply a restriction that makes the occurrence unavailable for all ordinary bookings before cutoff. Waiting and offered entries close as occurrence closed. The same closure behavior applies on removal of an occurrence from the schedule.
Source: choice: open entries should reflect an occurrence that can still be booked

### C-61: Reopening an occurrence does not revive closed entries.
Observable: Reopen bookings after an occurrence-wide closure or move a class after its old booking cutoff. If it is now bookable, eligible members may join again on a fresh action. Old entries remain closed.
Source: choice: old consent to wait should not silently recur after closure

### C-62: An open occurrence retains its queue through a schedule edit that keeps booking open.
Observable: Change the start time of the same occurrence without making it unavailable or passing its closing time. Existing waiters keep their turns in that occurrence.
Source: choice: a change to the same open occurrence need not forfeit queue priority

### C-63: An offer deadline is shortened when the new waitlist closing time precedes its current deadline.
Observable: Move an open occurrence's cutoff earlier than a live offer's deadline. The offer shows the earlier cutoff. The earlier cutoff becomes the current deadline.
Source: choice: the posted claim window cannot outlast booking or be extended by an unrelated schedule edit

### C-64: An occurrence edit that invalidates a claim prevents it from confirming after the edit takes effect.
Observable: Race a claim against cancellation, cutoff, or a capacity change that withdraws its hold. A winning claim is a booking subject to existing class policy. An invalidation effective first prevents the claim from taking a seat.
Source: choice: claim confirmation depends on current availability at the time it is made

### C-65: A permitted capacity reduction keeps only as many offers as fit after existing ordinary commitments.
Observable: Reduce capacity with active holds until only 1 of 2 offers fits. The offer for the earlier queue entry keeps its seat. Where ordinary checkout holds or other ordinary seat holds are still effective after the change under existing rules, they consume capacity alongside confirmed bookings. If those ordinary commitments exhaust capacity, no offers remain active.
Source: choice: preserve current bookings and give earlier queue entries priority if fewer holds fit

### C-66: A hold displaced by capacity reduction returns its entry to its previous place among waiting members.
Observable: Remove a seat held by a live offer while the occurrence stays open. The recipient sees waiting status again. On the next opening the member's original join turn still applies.
Source: choice: a class edit should not penalize the member who had received an offer

### C-67: A recovered waitlist honors existing queue turns.
Observable: Interrupt assignment, cause an ordinary cancellation, and restore service while more than 1 eligible member is waiting. The first new offer goes to the earliest eligible waiting entry.
Source: choice: recover from current bookings, holds, and class state without requiring members to join again

### C-68: A duplicate availability update cannot create an extra offer for the same opening.
Observable: Deliver one cancellation twice or deliver an older availability update after a newer one. Live offers reflect current free seats rather than the number of updates received.
Source: choice: repeated or late updates must not overallocate seats

### C-69: A live offer is visible in the recipient's app.
Observable: While signed in, reopen the occurrence or the in-app offer entry after an offer is issued. The current offer is visible and actionable for that member.
Source: choice: in-app delivery covers the initial release without depending on email, SMS, or push

### C-70: An offer notice directs the member to the current offer state.
Observable: Open an in-app notice after the offer has expired, been withdrawn, been displaced by capacity, or been claimed. See the current result for that offer in place of a live claim action.
Source: choice: stale notices cannot authorize a booking

### C-71: Disabling the waitlist closes active entries.
Observable: Turn the feature off with waiting and offered entries. The entries end as waitlist disabled and their offers stop holding seats.
Source: choice: stopping the service must leave capacity usable through ordinary booking

### C-72: Re-enabling the feature starts with no entries carried over from the disabled period.
Observable: Disable with open entries, then enable again. Members can choose to join anew where eligible. Their closed entries do not regain active status.
Source: choice: enrollment expresses a current intent to wait

### C-73: If waitlist shutdown takes effect before a claim confirms, the claim cannot confirm.
Observable: Overlap a disable action with a claim. If disablement is effective first there is no new booking. If the claim confirms first, it is an ordinary confirmed booking.
Source: choice: a confirmed booking survives shutdown and unconfirmed offers do not

### C-74: The booking app's effective clock decides whether a waitlist or claim deadline has been reached.
Observable: Set a device clock ahead or behind and attempt to claim near the deadline. The result follows the same deadline used by the booking app for other sessions.
Source: choice: members with different device clocks need the same claim window

### C-75: Offer expiry does not require an open member session.
Observable: Close all member sessions after creating a live offer. Return after its deadline. The old offer is expired, and any subsequent assignment uses the actually available seat.
Source: choice: a recipient who leaves the app cannot hold a seat past the deadline

### C-76: An occurrence's deadline follows the booking app's existing interpretation of its scheduled start.
Observable: Open the same occurrence on devices using different time zones. The deadline represents the same point in time on both. Where the scheduling system uses a local date and time, it supplies the occurrence's actual start instant. Its time zone and daylight-saving rules are unconfirmed.
Source: choice: the existing scheduling runtime's interpretation of start time binds when a seat can be claimed

### C-77: Waitlist actions follow the deployed booking app's session validity rules.
Observable: Attempt a protected waitlist action with a session the existing booking app regards as expired or revoked. The app requires a valid session before accepting it. The authentication provider and its session lifetime are unconfirmed.
Source: choice: the existing authentication runtime determines whether an authenticated booking identity is available

### C-78: A waitlist request that exceeds the deployed request limit can be recovered through the app.
Observable: Cause a request to stop responding at its host or gateway limit, then reload the occurrence or retry the original action after service returns. The member can determine whether the action committed by observing the authoritative entry or booking. The host, gateway, and effective timeout are unconfirmed.
Source: choice: the deployed execution runtime may stop a response before the member sees whether an action committed

### C-79: The waitlist is usable beyond development only when the deployment can recognize existing members and occurrences.
Observable: Open a deployed full occurrence using an existing member account after enabling the feature. The waitlist is available only in a deployment able to verify that identity and read current occurrence data. The hosting prerequisites are unconfirmed.
Source: choice: the existing authentication and booking services supply the identity and class state needed for any valid join

### C-80: Claim completion in a live deployment requires the ordinary booking dependencies for that occurrence.
Observable: In a deployment where a required payment, terms, or booking service is unavailable, try completing a claim that needs it. The app cannot confirm until the dependency allows completion. Providers, their production prerequisites, and their time limits are unconfirmed.
Source: choice: the existing booking services' completion rules also bind seats obtained via the waitlist

### C-81: Waitlist requests that cannot be processed within a deployment's supported operating limits produce a recoverable service failure where the app can respond.
Observable: Exceed an actual deployment request-rate, payload, or storage limit, if present. The caller sees a refused or uncertain result as appropriate and can check the current outcome once service returns. The runtime, applicable limits beyond these examples, and their numeric values are unconfirmed.
Source: choice: deployed infrastructure can reject work independently of class or waitlist capacity

### C-82: Existing confirmed bookings remain confirmed when waitlists are enabled.
Observable: Record the confirmed reservations for a full occurrence, enable the feature, and check the same reservations. They retain their booking identities and confirmed status.
Source: implied: U-6 adds waitlist service to an app with existing booking data

### C-83: A confirmed waitlist claim appears through ordinary booking views.
Observable: Claim an offer and open the member's existing reservations view. It shows the booking for the occurrence in the same way that it shows an ordinary reservation.
Source: implied: U-3 obtains a booking

### C-84: Confirmed waitlist bookings follow ordinary cancellation rules.
Observable: Cancel a booking obtained by claiming an offer. The existing permissions, applicable deadlines, and resulting booking status are the same as for an ordinary booking of the same occurrence. The deployed cancellation rules and numeric deadlines are unconfirmed.
Source: implied: U-2 directs confirmed members to ordinary booking cancellation

### C-85: Confirmed waitlist bookings follow existing occurrence cancellation handling.
Observable: Cancel an occurrence containing a direct booking and a waitlist-derived booking. Both receive the existing cancellation treatment. Any deployed refund and notification rules are unconfirmed.
Source: implied: U-7 manages occurrences using ordinary class controls

### C-86: A full-class direct-booking race leaves an eligible member a path to the waitlist.
Observable: With the feature enabled, attempt to book the last public seat concurrently with another member who gets it. The losing member gets a path to join if the occurrence still meets join conditions.
Source: implied: U-5 should not turn away someone who encounters fullness during booking

### C-87: A recipient with an active offer is directed to claim it when they try to book the same occurrence.
Observable: Start ordinary booking for an occurrence for which the same account holds a live offer. The app routes the member to the claim instead of giving them a second reservation path.
Source: choice: one member needs one seat and one way to spend their hold

### C-88: A waitlist action cannot add a booking beyond the available capacity of its occurrence.
Observable: Race claims, direct bookings, and any existing staff booking action for the last seat. No waitlist action causes the confirmed seat count for that occurrence to exceed its configured capacity.
Source: implied: U-3 obtains an actual seat from an opening

### C-89: Every ordinary booking path honors active offer holds.
Observable: With the final seat held, attempt ordinary booking using any supported surface, including member web or app views and operator bookings if available. The seat cannot be allocated to a different member. The supported booking surfaces are unconfirmed.
Source: choice: the seat promised to a member must survive other ways of booking it

### C-90: Claiming an offer cannot create a second confirmed seat for the same member and occurrence.
Observable: Attempt simultaneous claims or claim while an ordinary booking for the same identity is confirming. The waitlist cannot produce a second booking once a confirmed booking exists.
Source: choice: each waitlist entry is for one member seat

### C-91: Joining a waitlist does not authorize a payment.
Observable: Join a full occurrence that normally requires payment. No payment authorization or charge results from joining.
Source: choice: the member has expressed interest before committing to a booking

### C-92: Receiving an offer does not authorize a payment.
Observable: Receive an offer for an occurrence that ordinarily requires payment. No payment authorization or charge results from receiving the offer.
Source: choice: members only commit through the claim

### C-93: A successful claim incurs the normal booking charge, if any.
Observable: Compare the charge for a waitlist claim to the applicable ordinary price for the same member and occurrence at confirmation. The claim has no waitlist surcharge. Existing prices, currency, and discounts are unconfirmed.
Source: choice: the waitlist provides access to ordinary booking

### C-94: A claim that never confirms leaves no net additional payment.
Observable: Interrupt a paid claim after authorization or payment but before a booking can confirm, then restore service. Any authorization or payment attributable to the failed claim is released or reversed through the existing payment flow. Applicable provider reversal timing is unconfirmed.
Source: choice: members pay for a completed booking

### C-95: Members cannot read another member's waitlist entry through a member-facing surface.
Observable: Open the class, notices, and any member-accessible waitlist entry or offer link as a different member. No other entry's member identity, queue order, status, or deadline is disclosed.
Source: implied: U-3 gives the offer to its recipient

### C-96: Waitlist operation preserves unrelated class bookings.
Observable: Join, leave, expire, and claim entries for one occurrence. Observe another occurrence's confirmed reservations. Those actions make no change to the other occurrence's bookings.
Source: implied: U-1 and U-3 concern the selected occurrence

### C-97: A failed waitlist request leaves ordinary confirmed reservations intact.
Observable: Make a join, withdrawal, assignment, or claim fail. Existing confirmed reservations retain their identity and state unless changed independently by an ordinary booking operation.
Source: implied: U-4 holds a waitlist action apart from existing bookings

### C-98: A rollback preserves confirmed bookings obtained while waitlists were enabled.
Observable: Disable the feature, verify that no live offer remains, and switch to the prior app version. Confirm that bookings obtained by waitlist claim are still readable and cancellable under the ordinary booking rules.
Source: choice: members should be able to rely on a confirmed reservation across a release rollback

### C-99: Existing data does not create waitlist entries during initial rollout.
Observable: Enable the feature for the first time with scheduled classes, confirmed reservations, and past booking refusals already present. Each class starts with an empty queue.
Source: choice: members must choose to join under the new policy

### C-100: The feature is initially disabled for an existing deployment.
Observable: Introduce the release into an existing app before any operator changes the setting. Ordinary booking operates with waitlist enrollment off.
Source: choice: the operator controls when the new behavior becomes available

### C-101: A booking confirmed from an offer can be charged at most once.
Observable: Confirm a paid claim while repeating the request from two devices. The member sees at most one charge for the resulting booking.
Source: choice: retries may recover a receipt without starting a second purchase

### C-102: An authorized operator can read the effective rollout setting.
Observable: After requesting a setting change, including when the request loses its response, reopen the controls. The operator can distinguish enabled from disabled.
Source: choice: deployment and rollback need a reliable current setting

### C-103: An unsuccessful rollout setting change preserves the last effective setting.
Observable: Cause an enable or disable change to fail before it takes effect. The operator still sees the last effective setting, and members see its corresponding behavior.
Source: choice: an operator should be able to distinguish a failed change from a committed change with a lost response

### C-104: Operator inspection shows each active entry's member identity, queue order, status, and claim deadline if offered.
Observable: Open the class waitlist with both waiting and offered entries. Identify the member and relative turn for each entry, determine which have offers, and locate each offer's deadline.
Source: choice: these are the details needed to verify queue movement

### C-105: Operator inspection shows when an occurrence has no active waitlist entries.
Observable: Open the waitlist for an occurrence that never had an entry or whose entries have all ended. See an empty queue.
Source: choice: the operator needs to distinguish an empty queue from a failure to read it

### C-106: The operator view shows whether affected waitlist processing is available.
Observable: With the operator view reachable, inspect an occurrence when processing is available, unavailable, and unable to be verified. The view distinguishes those 3 conditions.
Source: choice: an empty queue alone does not establish that the service is healthy

### C-107: Waitlist administration adds the controls to enable enrollment, disable enrollment, read the effective setting, and inspect a class's waitlist.
Observable: As a feature administrator with class management access, locate these controls. The release does not require manual offers, queue edits, per-class overrides, or a recovery command because entries progress automatically from current class state.
Source: choice: these controls cover rollout, verification, and shutdown while leaving class edits in ordinary management

### C-108: The app puts a new offer where the recipient can find it through an in-app notice without reopening the specific class first.
Observable: As the recipient, open the app after an offer is issued. Find the notice and follow it to its current offer state. External email, SMS, and push delivery are outside this release because the existing channels are unconfirmed.
Source: choice: a member should be able to find an offer without checking each class

### C-109: One issued offer produces at most 1 in-app offer notice for its recipient.
Observable: Reprocess the same opening or recover from an interrupted notice publication. Find no duplicate notice for the same offer. A later offer after a displaced seat is a new offer.
Source: choice: repeated availability processing should not resemble multiple offers

### C-110: An available seat with an eligible waiter is offered within 60 elapsed seconds of continuous healthy operation.
Observable: Keep a seat available for assignment, an eligible member waiting, the waitlist open, and the services needed to check availability and eligibility and publish the offer working throughout. An offer is issued within 60 seconds after all those conditions first hold together. After an outage a new 60-second window starts when the conditions hold again. If the waitlist closes within the window, an offer may issue only before closure.
Source: choice: a bounded wait prevents a vacancy from sitting idle while members are waiting

### C-111: An issued offer's in-app notice is discoverable when that offer becomes active.
Observable: At the first point an offer is live, inspect the recipient's notices with the app reachable. The offer is discoverable there.
Source: choice: a member should get the full claim window with the offer accessible in the app

### C-112: The app refuses a new direct booking if it cannot establish whether waitlist priority permits that booking.
Observable: Free a seat during an enabled waitlist outage that prevents checking the queue or live holds. Attempt direct booking for the seat. The app reports a temporary failure or retry path instead of confirming an unverified seat.
Source: choice: an outage must not let a new arrival bypass a possible hold or waiter

### C-113: The app does not present an unverified join, leave, or claim as successful.
Observable: Interrupt the app's ability to determine an action result while the screen is reachable. The app shows that status cannot be verified and provides a way to read the current result after service returns.
Source: choice: a member needs an accurate distinction between a confirmed action and an uncertain one

### C-114: A fresh waitlist action refused for a known reason communicates that reason to the authorized member.
Observable: Try an applicable action with the feature disabled, the occurrence closed, a seat available directly, an existing booking, unmet eligibility, an earlier withdrawal, or an expired or superseded offer. The member can distinguish the applicable result for an accessible class. For missing, malformed, or inaccessible targets, a generic unavailable result suffices to avoid disclosing protected information.
Source: choice: members need the appropriate next action while access rules still apply

### C-115: A member whose offer was displaced can use a new offer for the same entry.
Observable: Reduce capacity to displace a hold, then restore capacity while the member still qualifies. If the member is next, they receive a new offer with a deadline calculated from the new issuance. An old claim remains invalid.
Source: choice: a replacement offer gives a fresh decision window

### C-116: An occurrence that closes at an offer's deadline ends the still-active entry as occurrence closed.
Observable: Issue an offer whose deadline equals booking cutoff or class start. Reach that instant with the offer unused. The entry shows occurrence closed.
Source: choice: the reason for ending the opportunity is that no new booking can be made

### C-117: A completed ordinary reservation ends the same member's active waitlist entry for that occurrence.
Observable: Where an existing authorized booking path can confirm a seat for that member without a claim, complete it while the member has an active entry. The entry ends as confirmed and releases any hold it still has.
Source: choice: someone who already secured the seat no longer needs queue priority

### C-118: A booking canceled after confirmation does not restore its waitlist entry.
Observable: Claim a seat, cancel that booking normally, and look for the former place in line. The old entry stays closed. The member can request a new turn only when ordinary join conditions hold.
Source: choice: a canceled booking does not express new intent to wait

### C-119: A closed entry is subject to the existing app's retention and deletion rules for member booking activity.
Observable: Once the applicable deletion or retention process has removed a closed entry, open an old authenticated entry reference. It yields an unavailable result rather than exposing removed data. The applicable retention period is unconfirmed.
Source: choice: use the app's existing member-data lifecycle without choosing a new retention period

### C-120: A deleted or unavailable historical reference cannot start a new waitlist action.
Observable: Replay a request targeting an old entry or offer whose history is no longer available. No fresh entry, offer, or booking is created.
Source: choice: cleanup must not turn a retry into a new request

### C-121: Membership access is checked before revealing an old entry or offer result.
Observable: Revoke a member's access to an occurrence after issuing their offer. Try reopening it or retrying a completed claim. No protected occurrence or entry detail is disclosed through the old reference, even if the referenced action had succeeded.
Source: choice: historical results have the same access boundary as active results

### C-122: Deletion of a booking identity closes its active entries as ineligible.
Observable: Delete an identity with a waiting entry or live offer through the app's existing account lifecycle. Its entries are no longer active in affected queues.
Source: choice: an entry attached to a removed account cannot produce an eligible booking

### C-123: Processing uses current class and booking state to recover unassigned openings.
Observable: Lose the update about a cancellation while the assignment service is unavailable. After recovery, an eligible waiter receives a seat if current data still shows the opening. An old update cannot allocate a seat already filled.
Source: choice: recovery needs to work even when an opening signal is lost

### C-124: An unavailable eligibility check does not close an entry as ineligible.
Observable: Interrupt the eligibility check while considering a waiter or processing a claim. The app cannot assign or confirm a seat based on that check and preserves the entry except for independent events such as an elapsed deadline or occurrence closure.
Source: choice: an unavailable answer differs from a confirmed refusal

### C-125: A waitlisted member is rechecked for eligibility before assignment.
Observable: Join as eligible, then lose a booking entitlement while waiting. Free a seat. The member receives no offer based on their earlier eligibility.
Source: choice: a past eligibility result cannot reserve a seat today

### C-126: A member's live hold remains valid through a transient booking service failure until an ordinary offer-ending event occurs.
Observable: Interrupt booking completion and restore it before the displayed deadline, with no intervening withdrawal, successful booking, loss of eligibility established at claim, displaced hold, occurrence closure, or disablement. The same offer is still claimable.
Source: choice: loss of service alone should not forfeit an otherwise valid hold

### C-127: An outage does not pause an issued offer's deadline.
Observable: Issue an offer, interrupt access past its deadline, and restore service. The old offer is expired if the occurrence remained open and the feature remained enabled.
Source: choice: a deadline remains predictable for the recipient and subsequent waiters during interruptions

### C-128: A delayed offer cannot be issued for a closed waitlist.
Observable: Free a seat just before the waitlist closes and delay processing until the cutoff, class cancellation, occurrence-wide restriction, or feature disablement is already effective. The app creates no live offer from that opening.
Source: choice: delayed processing cannot create an unclaimable reservation

### C-129: Waitlist assignment failure does not undo a confirmed ordinary cancellation.
Observable: Cancel a booking while assignment is unavailable, under otherwise valid ordinary cancellation conditions. Confirm the booking's cancellation through ordinary booking views before waitlist processing recovers.
Source: choice: an availability side effect cannot reverse the user's completed cancellation

### C-130: A booking attempt that is already in progress has no queue priority merely because it started earlier.
Observable: Start ordinary booking before an opening is available, then let an eligible waiting member gain priority for the opening before the attempted booking would confirm. The ordinary attempt cannot take the seat. Any ordinary reservations or checkout holds already effective under the app's existing rules still count in current availability. The existing pre-confirmation hold rules and durations, if any, are unconfirmed.
Source: choice: being first to an unconfirmed screen does not bypass a current queue or invalidate an existing commitment

### C-131: Waitlist assignment never uses a seat currently held under ordinary booking rules.
Observable: Where ordinary checkout or other existing booking rules temporarily hold seats, fill the class with existing reservations and such holds, then join. No offer uses a held seat before it is released. Existing hold types and their durations are unconfirmed.
Source: choice: the waitlist uses capacity the existing app has actually made bookable

### C-132: The release of an ordinary booking hold is treated as an opening.
Observable: If the existing app supports ordinary holds, release one while the occurrence is open and an eligible member is waiting. The waitlist can use the resulting opening.
Source: choice: the waitlist acts on a bookable seat regardless of how it became free

### C-133: A retry after a later rollout change cannot reapply an earlier completed setting change.
Observable: Disable the feature, re-enable it as a separate action, then retry the original completed disable request. The app retains the current enabled setting.
Source: choice: replay cannot undo a later operator decision

### C-134: A terminal entry keeps the reason that first ended it.
Observable: Withdraw an entry just before the occurrence closes, then check it after closure. It stays withdrawn. If expiration and the occurrence's booking cutoff are due at the same instant, the occurrence closure outcome applies. If disablement and an independent closure or expiry contend for the same active entry, the first effective transition wins.
Source: choice: delayed processing cannot overwrite a result or retroactively change why an opportunity ended

### C-135: The member can leave while an occurrence is visible even if ordinary booking eligibility has changed.
Observable: Make a waiting member ineligible for new bookings without removing access to the occurrence, then have them withdraw their still-active entry. The withdrawal succeeds.
Source: choice: refusing a new booking should not force a member to keep waiting

### C-136: Refreshing a status cannot change the member's queue turn.
Observable: Open the active entry repeatedly from the same or another device. The relative join order remains the same.
Source: implied: U-1 distinguishes checking an existing enrollment from joining anew

### C-137: Offer assignment pauses for an occurrence if the next waiter's eligibility cannot be determined.
Observable: Free 2 seats with 2 waiting members while the first member's eligibility result is unavailable. The later member does not receive an offer until the app can determine the first member's eligibility or that entry has left the queue.
Source: choice: a dependency failure should not silently reorder the queue

### C-138: Available capacity excludes all seats already committed under booking rules or queue priority.
Observable: Check public availability against the configured capacity after subtracting confirmed seats, ordinary holds if present, active offer holds, and openings owed to eligible waiting entries before offers issue. Count each seat at most once. A result at or below zero is shown as zero seats available.
Source: choice: the public booking path and the waitlist need the same account of which seats are free to book

### C-139: A closed waitlist entry holds no seat.
Observable: Check availability after an entry ends as withdrawn, expired, confirmed, ineligible, occurrence closed, or waitlist disabled. No seat is still committed to that entry's offer. A resulting confirmed booking counts as a booking.
Source: choice: a closed entry cannot keep capacity reserved

### C-140: An occurrence with no verified waitlist data is not shown to an operator as having an empty queue.
Observable: With the operator view available, interrupt access to the affected occurrence's entries. The view states that entries cannot be verified rather than reporting zero active entries.
Source: choice: an unverified queue is unsafe to use as evidence for rollback

### C-141: A delayed waitlist action cannot restore a closed entry.
Observable: Change the occurrence or feature to close an entry, then deliver a stale assignment, leave, or claim for that entry after the occurrence or feature reopens. That entry stays closed.
Source: choice: late work must not recreate earlier enrollment

### C-142: A later closing time does not extend an offer's current deadline.
Observable: Shorten a live offer's deadline by moving the occurrence cutoff earlier, then move the cutoff later before the shortened deadline. The displayed offer deadline stays at the shortened time.
Source: choice: a recipient can rely on the deadline already shown

### C-143: An offer-processing interruption for one occurrence does not suspend another occurrence whose dependencies still work.
Observable: Make eligibility unavailable for the first waiter in one class while another class can still check its members and process openings. The other class continues to make offers.
Source: choice: one queue's partial failure should affect only the bookings that depend on it

### C-144: A member can check the most recent closed outcome for a visible occurrence while that outcome is retained.
Observable: After an entry closes, reopen the occurrence in the waitlist-capable app with that member's account. With no newer entry, the app lets the member distinguish the closed outcome from current enrollment, including after enrollment is disabled.
Source: choice: a waiting member needs a way to learn why the entry ended

### C-145: The ordinary booking controls are available from a waitlist result that shows a confirmed booking.
Observable: Claim an offer, then reopen the result or attempt to leave the former entry. Follow the app's path to manage the confirmed booking, where ordinary cancellation is available when its rules allow it.
Source: choice: after confirmation a member must use booking management to give up the seat

