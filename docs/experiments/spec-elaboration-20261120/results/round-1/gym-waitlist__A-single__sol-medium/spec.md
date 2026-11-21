## Use cases

### U-1: A member joins a full class's waitlist to get a chance at a place
Flow: The member opens a bookable class session with 0 places available, chooses to join its waitlist, then sees that they are waiting. The member can return later to check their status.
Source: request

### U-2: A member books a class with room to secure a place immediately
Flow: The member opens an eligible session with 1 place available and nobody waiting. They book through the existing flow and see the usual result.
Source: implied: Adding a waitlist for full classes leaves ordinary booking in place.

### U-3: The first member joins an empty waitlist to be considered when space opens
Flow: A session with capacity 1 has 1 confirmed booking and 0 waiting members. An eligible member joins and becomes the only waiting member.
Source: implied: The request applies as soon as a class fills, including before anyone has joined its waitlist.

### U-4: A returning member repeats a join to check whether it worked
Flow: A member submits the same join again after a timeout or from a second tab. They can tell whether they are already waiting. They still have only 1 active entry for that session.
Source: implied: A member may retry when the first submission's outcome is unclear.

### U-5: A waiting member leaves to give up their chance at a place
Flow: A member who can no longer attend leaves the session's waitlist and sees that they are no longer waiting. They can still use the ordinary booking or waitlist options if they later change their mind.
Source: implied: A member's availability may change before a place opens.

### U-6: A booked member cancels so their reserved place can be released
Flow: A member uses the existing cancellation flow. If cancellation releases the only place in a full session, a waiting member can get it. If 0 people are waiting, the place becomes available through ordinary booking.
Source: implied: A waitlist needs a path from waiting to booking when a reserved place is released.

### U-7: Multiple waiting members get places as capacity becomes available
Flow: Three eligible members join a full session in sequence. While the session remains bookable, 2 places open. Two members move into confirmed bookings and 1 remains waiting.
Source: implied: A class can have multiple waiting members or multiple openings.

### U-8: An eligible member joins a long waitlist to keep a chance at a place
Flow: The member opens a full session with many people already waiting and joins it. The session's enrollment limit still applies to confirmed bookings.
Source: implied: A session stays full even when many people have already joined its waitlist.

### U-9: Concurrent members try for the same session without exceeding its capacity
Flow: Two people try to join at the same time. Later, an ordinary booking request overlaps the release of the final reserved place. The members see the outcomes that actually took effect, with at most 1 confirmed booking for that place.
Source: implied: Joining, booking, and cancellation can overlap for the same session.

### U-10: A member acts on a stale full-class view to find the currently available option
Flow: The member opens a full session showing a waitlist option. The last reserved place is released with nobody waiting before they submit the join. They see that they can now book the class.
Source: implied: Availability can change after a member opens a session.

### U-11: A booked or ineligible member tries to join and learns why the action is refused
Flow: A member tries to join while already booked, while signed out if the app requires sign-in, or while subject to a booking restriction other than capacity. They see a refusal applicable to their situation and gain no active entry.
Source: implied: Fullness is the barrier the waitlist is intended to address.

### U-12: A member submits an invalid waitlist action and learns that it failed
Flow: A caller submits a join for a missing or unknown session, or tries to leave an entry they do not control. The caller sees that the action did not succeed.
Source: implied: Callers can submit incorrect session information or act without the required permission.

### U-13: A waiting member becomes ineligible before a place opens
Flow: Two members are waiting. The earlier member becomes ineligible under the existing booking rules. A place opens and the next eligible member can get it.
Source: implied: Eligibility can change between accepting a waitlist entry and allocating a place.

### U-14: A member checks a waitlist after the session stops accepting bookings
Flow: A session reaches its existing booking cutoff, starts, or is cancelled. A waiting member checks their status and sees that the waitlist can no longer lead to a booking.
Source: implied: Waiting only serves its purpose while the session can still be booked.

### U-15: A scheduler edits capacity to control how many places the session offers
Flow: Where the app supports capacity edits, a scheduler uses the existing controls. An increase that opens a place can move a waiting member into the class. Lowering capacity to the confirmed booking count leaves 0 places to allocate.
Source: implied: Capacity can change through existing scheduling actions as well as through cancellations.

### U-16: A member confirms the right session after joining one occurrence of a class
Flow: The member joins one occurrence of a recurring class, then checks another occurrence of the same class. Their waitlist status belongs to the occurrence they selected.
Source: implied: Two sessions of the same class can have different availability.

### U-17: An operator starts the updated app with existing data so classes can use waitlists
Flow: The operator starts the updated version against the current data. Existing bookings and class settings still apply. A session already at capacity can accept its first waitlist entry.
Source: implied: The feature is being added to an existing booking app.

### U-18: An operator restarts the app after an interruption so waiting and booking can continue
Flow: After members join, the app stops. The operator restarts it. Members can see their persisted status. If capacity was released before the interruption, the app finishes allocating available places to eligible members.
Source: implied: Waiting can span restarts and a cancellation can be interrupted.

### U-19: An operator rolls back to keep ordinary booking available
Flow: The operator returns to the previous version with existing bookings, newly confirmed bookings, and pending waitlist entries present. Ordinary booking resumes under the previous version. When the updated version returns, pending entries are evaluated against current availability and eligibility.
Source: implied: The operator may need to go back to the previous version while bookings and waitlist entries exist.

### U-20: A member tries to withdraw after getting a place so they can avoid attending
Flow: The member opens an active entry. The app confirms their booking before their withdrawal takes effect. The member can tell that they now have a booking and can use the existing cancellation flow if they want to give it up.
Source: implied: The withdrawal in U-5 can overlap the allocation in U-6.

## Clauses

### C-1: An otherwise eligible member can join the waitlist of a full bookable session
Observable: With 0 places available, a member who meets the other booking conditions can submit a join that takes effect.
Source: request

### C-2: A successful join gives the member a visible waiting status
Observable: After joining, the member can tell that their request put them on the session's waitlist.
Source: implied: U-1 needs the member to know whether joining worked.

### C-3: The member can retrieve their current waitlist or booking status later
Observable: After leaving the session view and returning, the member can tell whether they are still waiting, have a confirmed booking, or are no longer waiting.
Source: implied: The opportunity in U-1 may arise after the member leaves the booking flow.

### C-4: A pending waitlist entry uses 0 places against session capacity
Observable: In a session with capacity 1 and 1 confirmed booking, an eligible member joins the waitlist. The session still counts only the 1 confirmed booking toward capacity.
Source: implied: U-3 distinguishes waiting for a place from using one.

### C-5: A session with no prior entries accepts its first eligible waitlist member
Observable: With 0 waiting members and 0 available places, an eligible member joins and has an active entry.
Source: implied: U-3 is the first use of the feature for a full session.

### C-6: One member can have at most 1 active waitlist entry per session
Observable: A member submits multiple joins for the same session, including overlapping submissions, and has at most 1 active entry for it.
Source: implied: U-4 retries one request for a place.

### C-7: A repeat join tells the member when their earlier entry is still active
Observable: A member repeats a join while already waiting and can tell that their entry still exists.
Source: implied: U-4 must resolve uncertainty after the original response is lost.

### C-8: A member can withdraw their active waitlist entry
Observable: A member leaves a waitlist they joined, after which that entry is no longer active.
Source: choice: U-5 gives members control when they can no longer attend.

### C-9: A former waiting member can join again when they satisfy the current join conditions
Observable: A member leaves a waitlist. While the same session is still full and bookable, the member joins again with 1 active entry.
Source: implied: U-5 leaves the member eligible for the general join action in U-1.

### C-10: A withdrawn entry cannot receive a place released after the withdrawal takes effect
Observable: The only waiting member withdraws successfully. When 1 place subsequently opens, the member remains without a booking.
Source: implied: U-5 gives up the chance attached to the withdrawn entry.

### C-11: A released place can go to an eligible waiting member
Observable: An eligible member waits for a full session. A confirmed cancellation opens 1 place during the booking window, and the member can get that place through the waitlist.
Source: implied: U-6 turns waiting into a chance to attend.

### C-12: The app automatically confirms a booking for the selected eligible waiting member when a place becomes available
Observable: With 1 eligible member waiting and 1 place released, a member who satisfies the requirements for confirmation gets a confirmed booking without taking a further waitlist action.
Source: choice: Automatic allocation fills available places without a separate claim window.

### C-13: Joining discloses that an available place may be booked automatically
Observable: Before committing to join, the member can tell that joining authorizes automatic booking subject to the existing booking requirements.
Source: choice: U-1 needs informed consent for the automatic booking in U-6.

### C-14: Allocation selects eligible entries in the order those entries became active
Observable: Two eligible members join one after the other. If only 1 place opens while both are eligible, the earlier member receives the place.
Source: choice: The time each member began waiting provides a predictable priority rule.

### C-15: An opening is allocated to the waitlist before ordinary bookings can take it while an eligible member is waiting
Observable: An ordinary booking request overlaps the release of 1 place while an eligible entry is active. The place goes through the waitlist.
Source: choice: Priority over new requests makes waiting worthwhile when there is competition for a place.

### C-16: Every available place can be allocated while an eligible entry remains
Observable: If 2 places open in a bookable session with 3 eligible waiting members, 2 of those members can get places.
Source: implied: The same opportunity applies to each opening in U-7.

### C-17: Waiting entries that receive no place stay active while the session remains bookable and the entries remain eligible
Observable: With 3 eligible waiting members and 2 places allocated, 1 eligible member is still waiting.
Source: implied: U-7 gives the remaining member a chance at later openings.

### C-18: A confirmed booking obtained through the waitlist ends the associated waiting status
Observable: After a member receives a confirmed booking through the waitlist, they have 0 active entries for the session.
Source: implied: U-6 has fulfilled that member's request for a place.

### C-19: The waitlist has no separate per-session enrollment limit
Observable: An otherwise eligible member can join a full bookable session regardless of the number of existing waiting entries.
Source: choice: The request gives no queue-size limit, and an additional cap would turn away eligible members for a reason other than class capacity.

### C-20: Waitlist allocation respects the session's existing capacity
Observable: In a session with capacity 1, allocating a place through the waitlist never causes the confirmed count to exceed 1, even when requests overlap.
Source: implied: U-9 allocates available places within the same limit that made the class full.

### C-21: Overlapping join and capacity changes leave each affected member with an accurate outcome
Observable: A join overlaps the release of the final reserved place. After both actions settle, the member can tell their resulting status or whether the session has ordinary booking availability.
Source: implied: U-9 and U-10 need a result that reflects the actions that took effect.

### C-22: A stale join request for a session with a place available directs the member to the ordinary booking option
Observable: A member attempts to join after the session regains ordinary availability. They learn that they can book it through the existing flow.
Source: choice: In U-10 the member intended to join a full session, so the app presents the available booking decision.

### C-23: Confirmed members cannot join the waitlist for the same session
Observable: A member with a confirmed booking for the selected session submits a join and receives a refusal identifying their existing booking.
Source: implied: U-11 already has the place the waitlist offers.

### C-24: Waitlist actions honor the app's existing sign-in requirements
Observable: Where booking requires sign-in, a signed-out caller who attempts to join receives the applicable sign-in requirement.
Source: implied: U-11 uses the app's existing way to identify the member requesting a place.

### C-25: The waitlist preserves the existing booking eligibility rules other than fullness
Observable: A member subject to an existing restriction that makes them ineligible for the selected session is refused when they attempt to join, with a result that identifies the applicable restriction.
Source: implied: U-11 seeks relief from fullness while the underlying eligibility rules still apply.

### C-26: A join with a missing session selection is rejected
Observable: A caller submits a join with no session. The result identifies the missing selection.
Source: implied: U-12 requires a session to determine what the member wants to attend.

### C-27: A join for an unknown session is rejected
Observable: A caller submits a join for a session that does not exist. The result indicates that the session is unavailable or unknown.
Source: implied: U-12 cannot allocate a place in a nonexistent session.

### C-28: A member cannot change another member's entry without existing authorization to act for them
Observable: A caller lacking that authorization attempts to withdraw another member's entry and receives a refusal.
Source: implied: U-12 preserves control of actions taken on behalf of another member.

### C-29: A member's waitlist status follows the app's existing access rules for their booking status
Observable: A caller who lacks access to another member's booking status cannot retrieve that member's waitlist status.
Source: choice: The same access boundary protects the member's attendance intentions.

### C-30: A refused waitlist action leaves existing bookings and entries as they were
Observable: A rejected join or withdrawal makes 0 changes to the session's bookings or active waitlist entries.
Source: implied: The failed actions in U-11 and U-12 did not take effect.

### C-31: The app verifies current booking eligibility before confirming a booking through the waitlist
Observable: A member loses eligibility after joining. They receive 0 bookings through the waitlist while that restriction applies.
Source: implied: U-13 applies the existing eligibility rules at booking time.

### C-32: An ineligible entry cannot block allocation to another eligible waiting member
Observable: One waiting member becomes ineligible and 1 place opens while another waiting member meets the booking rules. The eligible member can receive the place.
Source: implied: U-13 still gives eligible waiting members a chance at the opening.

### C-33: An entry found ineligible during allocation stops waiting
Observable: When allocating a place, the app finds that a waiting member fails an existing eligibility rule. That member's entry is no longer active after the allocation attempt.
Source: choice: A member with a disqualified request can tell that their current wait has ended and can rejoin if they become eligible.

### C-34: A place obtained through the waitlist is subject to the existing requirements for booking confirmation
Observable: If the existing flow requires payment authorization, approval, or another prerequisite for the selected session, a member has a confirmed booking through the waitlist only after meeting that prerequisite.
Source: implied: U-6 produces a booking subject to the same confirmation rules as U-2.

### C-35: A session that has stopped accepting bookings refuses new waitlist joins
Observable: After the existing booking cutoff or another booking closure for the session, a member attempting to join sees that the session is closed to new entries.
Source: implied: U-14 offers a waitlist only where it can still lead to a booking.

### C-36: Waitlist allocation observes the session's existing deadline for accepting bookings
Observable: If 1 place opens at or after the point the ordinary booking flow closes, 0 new bookings are confirmed through the waitlist.
Source: implied: U-14 leaves the existing booking deadline in force.

### C-37: Closing a session to further bookings ends its active waitlist for that booking period
Observable: After bookings close, including through session cancellation, a previously waiting member can tell that their entry is no longer active.
Source: choice: U-14 gives members a definitive outcome when that wait can no longer lead to a booking.

### C-38: A capacity increase that releases places while bookings are open makes those places available to the waitlist
Observable: With 1 eligible member waiting, the scheduler increases a full session from capacity 1 to capacity 2 during booking. The new place can be allocated through the waitlist.
Source: implied: The capacity change in U-15 creates the same opportunity as an opening in U-6.

### C-39: Capacity changes retain the app's existing rules for confirmed bookings
Observable: Where capacity edits are supported, lowering capacity with confirmed bookings in place has the same effect on those bookings as in the previous version.
Source: implied: U-15 changes availability through the existing scheduling action.

### C-40: A waitlist entry applies to the selected session only
Observable: A member joins one occurrence of a class. A separate occurrence shows 0 entries for that member unless the member independently joined it.
Source: implied: U-16 keeps each occurrence's demand tied to its own places.

### C-41: Ordinary booking remains available when a session has an available place with nobody waiting
Observable: In the conditions of U-2, a member can complete the existing booking flow for the available place.
Source: implied: The request extends the full-class experience while the existing booking path remains available.

### C-42: An opening with 0 eligible waitlist entries becomes ordinary booking availability
Observable: A cancellation opens 1 place during booking with nobody waiting. The session shows 1 place available for ordinary booking.
Source: implied: U-6 keeps the existing empty-waitlist case usable.

### C-43: The app preserves the existing cancellation rules for confirmed bookings
Observable: Under identical eligibility and timing conditions, a member can cancel a confirmed booking under the same terms as before, including a booking obtained through the waitlist.
Source: implied: U-6 relies on the existing way to release places.

### C-44: Bookings obtained through the waitlist appear in the ordinary confirmed-booking view
Observable: After allocation and confirmation, the member finds the class among their other confirmed bookings.
Source: implied: The member who gets a place in U-6 needs the app's existing way to find their booking.

### C-45: Bookings obtained through the waitlist receive the app's existing booking confirmation feedback
Observable: If the app normally confirms a successful booking through an existing message or channel, a member booked through the waitlist receives that same type of confirmation.
Source: implied: U-6 gives members the ordinary confirmation that accompanies a booking.

### C-46: Existing confirmed bookings remain confirmed on upgrade
Observable: After the operator starts the updated app with current data, a member with a previously confirmed booking still sees that booking.
Source: implied: U-17 carries forward the existing bookings.

### C-47: Existing session capacities continue to apply on upgrade
Observable: A session with capacity 1 before upgrade still has capacity 1 after upgrade.
Source: implied: U-17 uses the current capacity to decide whether a session is full.

### C-48: Existing booking windows continue to apply on upgrade
Observable: A session with an existing booking window opens and closes to booking at the same times after upgrade.
Source: implied: U-17 carries forward the session's existing booking conditions.

### C-49: A session that predates the upgrade starts with 0 active waitlist entries
Observable: Immediately after upgrading a session with existing bookings, nobody has an active waitlist entry solely because of the upgrade.
Source: implied: U-17 adds the ability to ask for a place without enrolling anybody automatically.

### C-50: An existing full session can accept waitlist joins without new operator configuration
Observable: The operator starts the updated app with the existing class and booking settings. An otherwise eligible member can join the waitlist of a session that was already full.
Source: choice: The current settings determine when a class is full, so U-17 requires no additional setup to activate the feature.

### C-51: Active waitlist entries survive a restart
Observable: A member whose join completed before a restart still has their entry afterward when the class remains full and the member remains eligible.
Source: implied: U-18 continues a member's wait through interruptions.

### C-52: Restart preserves the allocation priority of entries that are still waiting
Observable: With the same waiting members and eligibility, the single place released after a restart goes to the same member who would have received it without the restart.
Source: implied: U-18 resumes each member's existing wait.

### C-53: Allocation resumes for available places after an interruption
Observable: A cancellation takes effect while an eligible member is waiting. If the app stops before allocation finishes, after restart the member can receive the available place while bookings remain open.
Source: implied: U-18 restores the waitlist's opportunity even if an opening occurred just before the interruption.

### C-54: Resuming an interrupted allocation cannot produce a duplicate confirmed booking for the same member and place
Observable: An allocation already created a confirmed booking before the app stopped. After restart, the member has exactly 1 confirmed booking from that allocation.
Source: implied: U-18 continues the interrupted work without repeating a completed reservation.

### C-55: The previous version can resume ordinary booking after rollback
Observable: The operator returns to the previous version after using waitlists. Members can book available places under that version's ordinary booking rules.
Source: implied: U-19 uses rollback to restore ordinary booking.

### C-56: Confirmed bookings survive rollback
Observable: After rollback, bookings that were confirmed before rollback still appear as confirmed, including places allocated through the waitlist.
Source: implied: U-19 preserves attendance commitments already made.

### C-57: Rollback does not convert pending entries into bookings
Observable: Immediately after rollback, a member whose entry was pending has gained 0 confirmed bookings as a result of the rollback.
Source: implied: U-19 carries forward only commitments that reached confirmation.

### C-58: Pending entries survive a rollback for use when the updated version returns
Observable: The operator rolls back and later starts the updated version again. In a session that stayed full and bookable, a member whose entry was pending and remains eligible is still waiting.
Source: choice: Preserving entries saves members from joining again after an operational interruption.

### C-59: After the updated version returns, allocation uses current session availability
Observable: If an ordinary cancellation during rollback leaves 1 place available in a session that remains bookable, an eligible pending member can get that place after the updated version returns.
Source: implied: U-19 resumes waiting against the live booking state.

### C-60: A withdrawal submitted after allocation leaves the confirmed booking in place
Observable: The member submits a withdrawal from a stale waitlist view after their booking was confirmed. The confirmed booking remains active.
Source: implied: In U-20 withdrawing an entry and cancelling a confirmed booking are different member actions.

### C-61: A late withdrawal tells the member when their entry has already become a booking
Observable: A member tries to withdraw an entry that has already been fulfilled. The result indicates that the member now has a booking.
Source: implied: U-20 needs the member to know which action applies to their current status.

### C-62: Simultaneous joins from different eligible members can both take effect
Observable: Two eligible members join the same full bookable session at the same time. Each can see their own active entry afterward.
Source: implied: The opportunity in U-9 applies independently to each member requesting a place.
