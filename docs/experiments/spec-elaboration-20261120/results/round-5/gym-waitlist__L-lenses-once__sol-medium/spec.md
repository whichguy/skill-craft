## Use cases

### U-1: A member opens a class session to find out how to get a place
Flow: The member opens a session they can access through the existing class booking flow. They see the ordinary booking action when they can book immediately. If the session is full and they qualify to wait, they can join its waitlist. If they already have a booking or a waiting place, the app shows that status. A session they cannot access reveals no waitlist information.
Source: request

### U-2: A member joins a full session to be considered for a place
Flow: The member chooses to join after seeing that joining authorizes an automatic booking for one place if eligible. Success leaves them with one waiting place for that session. If a place has opened for them before the join is accepted, the app directs them to ordinary booking. If the session is unavailable or the member is ineligible, the app explains that they could not join.
Source: implied: The request needs a way to accept interest when immediate booking is unavailable.

### U-3: A waiting member checks their status to know whether they have a booking
Flow: The member returns through the class booking flow and sees whether they are still waiting or have a confirmed booking. If their wait ended without a booking, the app stops showing them as waiting. If the app cannot determine the result, it indicates that the status is unavailable. The member cannot use this view to inspect other members' waiting places.
Source: implied: Joining is useful only if the member can tell what happened to their place.

### U-4: A waiting member leaves to withdraw permission to book a place
Flow: The member leaves their own waitlist entry. If the leave succeeds while they are still waiting, they stop waiting. If a booking won the race, they see the booking and can use the ordinary booking cancellation flow if eligible. A repeated leave has no additional effect. A later intentional join is treated as a new request.
Source: implied: Members need to be able to withdraw interest before it becomes a booking.

### U-5: A member cancels a booking so the released place can go to a waiting member
Flow: The member cancels through the existing cancellation flow. If the cancellation succeeds and frees a bookable place, the first eligible waiting member gets a confirmed booking. With zero eligible waiting members, the place returns to ordinary availability. A failed cancellation frees no place. A waiting member who receives the place can use the ordinary cancellation flow.
Source: implied: A waitlist must be used when a full session gains a place.

### U-6: Members act on the same session at once to try to get a place
Flow: Two members can join a full session at nearly the same time. When a place opens, the app resolves their order consistently. An ordinary booking cannot bypass an eligible waiting member. When more than one place opens, the same rules apply to each place. If demand exceeds availability, members without a place remain waiting while eligible.
Source: implied: Multiple members can request places for the same session.

### U-7: A member recovers after an interrupted request to find out what took effect
Flow: The member loses the response to a join, leave, booking, or cancellation. They return to the app to check the outcome or retry the same action. The app reflects the committed result and does not repeat the effect. If the operation did not finish, the member can distinguish an unresolved outcome from a confirmed success.
Source: implied: A missed or repeated request must not change who gets a place.

### U-8: A member loses eligibility while waiting so the place can go to someone who can take it
Flow: The member joins while eligible. Before they reach an available place, an existing rule makes them ineligible. When the app confirms that they cannot take the place, it ends their wait and considers the next member. If eligibility cannot be determined temporarily, the wait stays pending while the app recovers.
Source: implied: Being placed on a waitlist does not establish eligibility for a later booking.

### U-9: An operator changes a session through existing controls so the waitlist follows the session
Flow: If the app supports changing capacity or other booking conditions, the operator uses those controls. New bookable places go to waiting members in order. A reduction supplies no new places. If booking closes or the session is cancelled, future waitlist bookings stop. If the session is removed, a stale link or action cannot revive its waitlist.
Source: implied: A waitlist follows the availability and lifecycle of its class session.

### U-10: A member reaches the booking cutoff to know whether a place is still possible
Flow: The member checks before and at the cutoff. Before it, the member can wait if otherwise eligible. At the cutoff, joining closes and a pending wait cannot become a new booking. The member can still see a booking made before the cutoff wherever the existing app shows it.
Source: implied: A wait for a class must have an end even if a place never opens.

### U-11: An operator enables the release so existing sessions can accept waitlists
Flow: The operator makes the release available. Existing bookings and session availability carry forward. An existing full session can accept its first waiting member, and a session with availability still supports ordinary booking. If the waitlist cannot safely accompany booking, the operator keeps the release from accepting waitlist activity until it is ready.
Source: implied: Adding the feature to an existing app must account for the sessions and bookings already in use.

### U-12: An operator recovers an interrupted allocation to keep valid requests and bookings
Flow: The operator can establish whether a member is waiting or booked and whether an available place still needs to be allocated, using authorized access. After the dependency returns, interrupted allocation resumes for sessions still open. A booking committed before the interruption remains usable. If recovery happens after closure, the session receives no late promotion.
Source: implied: A failure between a place opening and its allocation must not lose the wait or repeat the booking.

### U-13: An operator rolls back the release to restore ordinary booking
Flow: Before returning to the previous release, the operator ends active waits and can verify their disposition. Confirmed bookings remain available in the previous release. Members whose waits ended can use ordinary booking if eligible. If the operator cannot verify that waits have ended or that bookings will remain available, rollback is held until those conditions can be verified.
Source: implied: The app needs a safe path back to the version before waitlists.

## Clauses

### C-1: A full class session has a waitlist.
Observable: For an accessible session with zero immediately bookable places because its capacity is taken, an eligible member without a booking can request a waiting place while waitlist admission is open.
Source: request

### C-2: A waitlist belongs to one scheduled class session.
Observable: When the same class is offered at two times, joining for the first time creates a waiting place only for that session.
Source: implied: U-1 and U-2 refer to the session the member is trying to attend.

### C-3: Session discovery follows existing access rules.
Observable: A member reaches a waitlist through an accessible session in the ordinary booking flow. A session hidden by the current access rules is not revealed through waitlist discovery. The existing access rules are unconfirmed.
Source: implied: U-1 exposes the waitlist for a session the member can access.

### C-4: The app distinguishes a full session from a session that is unavailable for another reason.
Observable: An eligible member can identify the waitlist action when capacity is taken. If the session is closed, cancelled, removed, or otherwise barred by an existing booking rule independent of capacity, the app does not present joining as a remedy. Any additional existing reasons are unconfirmed.
Source: implied: The request remedies full classes.

### C-5: A member who can currently book a place can use ordinary booking.
Observable: When a place is available to the member for immediate booking, the session provides the ordinary booking action.
Source: implied: U-1 preserves immediate booking when there is room for the member.

### C-6: Joining requires an affirmative action.
Observable: Opening or refreshing a session, or losing an ordinary booking attempt when the session fills, leaves the member with zero waiting places until they explicitly join.
Source: implied: U-2 makes joining the member's decision.

### C-7: A join requests one place for the acting member.
Observable: One successful join covers one place for the member whose account is acting. The waitlist offers no request for a guest, a different member, or a group.
Source: choice: One place for the person opting in serves the request without introducing delegated or group waitlist rules.

### C-8: Waitlist actions use the app's existing member identity requirement.
Observable: A person who has not met the app's existing identity requirement cannot join, inspect a personal wait, or leave one. The app follows its existing sign-in or identity recovery path where one exists. The exact identity requirement is unconfirmed.
Source: implied: U-2 through U-4 depend on knowing which member the wait belongs to.

### C-9: Existing non-capacity booking eligibility governs admission.
Observable: Try to join with the proposed member and session while the session is full. A rule that would refuse that member an ordinary booking even if a place were free also refuses admission. The app's complete existing eligibility rules, their exceptions, and their numeric thresholds are unconfirmed.
Source: implied: U-2 gives access to future openings within the same class booking rules.

### C-10: A confirmed booking for the same member and session prevents a waitlist join.
Observable: A member with a confirmed booking for the session has zero active waits for it after attempting to join. A past cancelled booking alone does not count as a confirmed booking.
Source: implied: U-1 and U-2 address members who need a place.

### C-11: The join action explains that allocation is automatic before the member commits.
Observable: Before joining, the member can tell that they are authorizing one ordinary booking for the chosen session if an eligible place becomes available.
Source: choice: Advance consent lets the app fill a place without a separate offer or a second member action.

### C-12: A session requiring a new member decision at booking time is ineligible for automatic allocation until that decision can be given through the ordinary flow.
Observable: Where an ordinary booking requires a payment authorization or other consent that cannot validly be obtained or applied through the join action, the app declines the join with a reason. The existence and parameters of such rules are unconfirmed.
Source: choice: Automatic allocation cannot substitute for a member decision that the existing booking flow requires.

### C-13: A successful join creates exactly one active waiting place.
Observable: After success, the member's session view shows that they are waiting for that session.
Source: implied: U-2 requires a durable result the member can see.

### C-14: One member can have at most one active waiting place for a session.
Observable: Two simultaneous joins or repeated joins for the same member and session leave one active waiting place.
Source: implied: U-2 grants one wait per member and session.

### C-15: Retrying a join while already waiting preserves queue priority.
Observable: A member who joined ahead of a second member can repeat their join and is still ahead of the second member when one place opens.
Source: implied: U-6 relies on a repeat attempt having no second effect.

### C-16: A join whose member can now book immediately returns the member to ordinary booking.
Observable: With zero active waits for the member and an immediately bookable place available to them at decision time, a stale join creates zero waits and directs them to book.
Source: choice: A join authorizes booking through the waitlist and a current open place can be taken through the existing booking flow.

### C-17: An invalid session selection cannot create a waiting place.
Observable: A missing, malformed, unknown, deleted, or inaccessible session selection fails with zero waits created from that action. The existing identifier format and its length limits are unconfirmed.
Source: implied: U-2 requires a valid session to wait for.

### C-18: An unaccepted join reports why the member could not join when that reason can safely be disclosed.
Observable: When the applicable outcome is immediate availability, an existing booking, failed eligibility, waitlist closure, or temporary inability to process the join, the member can distinguish it from a successful join. For missing, malformed, unknown, deleted, or inaccessible session selections, a generic unavailable outcome is sufficient.
Source: implied: U-2 and U-7 require the member to know the result without exposing restricted information.

### C-19: The waitlist adds no product cap on queue length.
Observable: For any supported session, the first eligible member and later eligible members can join even if there are already more waiting members than there are total places. No feature-level maximum is imposed. The runtime's supported upper bound is unconfirmed.
Source: choice: The request gives no reason to turn excess demand away at another product limit.

### C-20: The waitlist adds no product cap on the number of different sessions a member can wait for.
Observable: A member can join a second or subsequent eligible full session while waiting for an earlier one, subject to existing eligibility and runtime limits. Their exact limits are unconfirmed.
Source: choice: Existing eligibility can govern booking across sessions without a new waitlist quota.

### C-21: A waiting place consumes zero units of confirmed class capacity.
Observable: Joining increases the waiting count by one without increasing the confirmed booking count or reducing the confirmed capacity by one.
Source: implied: U-2 records interest in a future opening.

### C-22: A member can see their own current waitlist outcome from the booking flow.
Observable: For a session the member can access, returning to the flow shows whether they are waiting or have a confirmed booking. If a former wait ended without booking, the member sees that they are no longer waiting. A member who has never waited needs no history display.
Source: implied: U-3 needs to distinguish an active wait from a booking or a wait that has ended.

### C-23: Waitlist status is available without displaying a live queue position.
Observable: A member can check their outcome without a numeric position, total queue length, estimated wait time, or roster being required.
Source: choice: A member needs to know their own outcome. Changing estimates and other members' data are unnecessary for that purpose.

### C-24: A member cannot see another member's waitlist information.
Observable: Through the member booking flow or its member-facing calls, a member cannot obtain another member's identity, entry, join time, position, eligibility result, or allocation outcome. The same holds when the caller guesses a reference to a wait.
Source: implied: U-3 makes personal status private.

### C-25: A member cannot change another member's waiting place.
Observable: A member submitting a leave or join under someone else's identity cannot create, remove, or reorder that person's entry.
Source: implied: U-2 and U-4 allow a member to act on their own wait.

### C-26: An active waiting place can be withdrawn by its member.
Observable: If the member's leave takes effect while the wait is active, the session shows zero active waits for that member.
Source: implied: U-4 lets the member withdraw interest.

### C-27: Leaving the waitlist cancels zero confirmed bookings.
Observable: If a booking already exists when leave takes effect, the booking remains confirmed and the app shows the booking outcome. Cancellation requires the ordinary booking action.
Source: implied: U-4 distinguishes withdrawing interest from cancelling a booking.

### C-28: A repeated leave has no additional effect.
Observable: After withdrawal, repeating leave before any new join leaves zero active waits for the member and changes no other member's wait.
Source: implied: U-4 and U-7 require leave to be safe to repeat.

### C-29: An intentional rejoin starts a new wait in the current admission order.
Observable: If member A joins before member B, leaves, and then successfully rejoins after B, B is considered ahead of A when a place opens.
Source: choice: Withdrawal gives up the earlier priority. Rejoining uses the same rule as a first join.

### C-30: A waiting place authorizes no booking after withdrawal takes effect.
Observable: If leave takes effect before a promotion, a later opening cannot book the member using that wait, including when allocation work began before the leave.
Source: implied: U-4 withdraws the authority the app received at join.

### C-31: A newly bookable place is allocated automatically while the waitlist is open.
Observable: If the session gains one bookable place and has one eligible waiting member, that member receives one confirmed booking with no new action from the member or operator.
Source: choice: Advance authorization fills openings without an offer, a response deadline, or a manual allocation step.

### C-32: Waitlist priority follows the order in which successful joins take effect.
Observable: When two eligible members are waiting for one opening, the first accepted join wins. If attempts overlap, there is one consistent acceptance order even if their displayed times match or their responses arrive in the opposite order.
Source: choice: First-come priority gives members a predictable rule without requiring timestamp precision or a new priority system.

### C-33: Ordinary booking cannot bypass a waiting member entitled to a released place.
Observable: When a cancellation releases the only place and an eligible member is already waiting, a competing ordinary booking cannot consume that place before the waitlist has been served.
Source: implied: U-5 and U-6 require the waitlist to provide access to openings.

### C-34: Ordinary booking can use surplus places.
Observable: When two bookable places become available and exactly one waiting member can take one, the other place is available through ordinary booking.
Source: implied: U-5 and U-6 reserve places for actual waiting demand.

### C-35: A successful booking cancellation triggers allocation only when it releases a bookable place.
Observable: Cancelling one booking through existing rules supplies one place for allocation when one place is freed. A refused cancellation, a repeat cancellation of the same booking, or a cancellation that frees zero bookable places supplies zero places.
Source: implied: U-5 allocates actual vacancies.

### C-36: A capacity increase triggers allocation if it creates new bookable places.
Observable: If the existing app accepts a capacity change from 10 to 12 for a session with 10 confirmed places and two eligible waits while booking is open, the two newly bookable places go to those members.
Source: implied: U-9 treats openings created through existing capacity controls as openings for the waitlist.

### C-37: A capacity decrease supplies no new place to the waitlist.
Observable: If the existing app accepts a capacity decrease and the session now has zero bookable places, no promotion occurs because of the decrease.
Source: implied: U-9 follows actual availability.

### C-38: Allocation considers each currently bookable place.
Observable: If two places become available together with three eligible waits, exactly two members receive bookings in priority order and the third remains waiting while admission remains open.
Source: implied: U-6 applies the same allocation rule to each available place.

### C-39: A waitlist booking cannot exceed the session's current bookable capacity.
Observable: With one place remaining, simultaneous cancellations, capacity changes, ordinary bookings, and promotion attempts cannot produce two bookings against that place. If a decrease takes effect before allocation and leaves zero places, no promotion proceeds. The app's existing capacity formula and class-size limits are unconfirmed.
Source: implied: U-5, U-6, and U-9 share a single session capacity.

### C-40: Promotion rechecks existing booking eligibility at allocation.
Observable: A waiting member is booked only if the current booking rules allow the booking when it takes effect, including any eligibility changes made after the join. The complete existing rule set and its limits are unconfirmed.
Source: implied: U-8 treats a promotion as a real class booking.

### C-41: A definitive individual eligibility refusal ends that member's wait.
Observable: If the app can determine that the first waiting member cannot take the booking under existing rules, that member stops waiting without a booking and the next eligible member can receive the same place.
Source: choice: Ending the refused wait avoids leaving a member indefinitely queued for a place they cannot take.

### C-42: An unresolved eligibility check preserves the member's priority.
Observable: If an eligibility dependency cannot answer for the first member, the app preserves that wait and does not give its potential place to the next member while the result is unresolved. A place known to be surplus remains usable under the ordinary availability rule.
Source: choice: Temporary inability to check a member should not cost the member their position.

### C-43: Competition between operations is resolved against the state in which each takes effect.
Observable: With one opening, a join accepted before a competing booking claims the opening has the same priority as any other active wait. A join processed after a successful competing booking can wait for the next opening if eligible. Where an opening is immediately bookable at the join decision, the stale-join outcome applies.
Source: implied: U-2 and U-6 cannot use a stale display to commit conflicting outcomes.

### C-44: Promotion produces an ordinary confirmed booking for the waiting member.
Observable: After promotion the booking is usable through the same booking details and attendance flow the app supplies for a direct confirmed booking. The exact existing display and attendance capabilities are unconfirmed.
Source: implied: U-5 gives the member a place in class.

### C-45: The same member cannot have both an active wait and a confirmed booking for the same session.
Observable: As soon as a booking for the member and session takes effect, the member is booked and the wait ceases to be active, whichever existing booking path supplied the place.
Source: implied: U-1 and U-5 use waiting only while the member needs a booking.

### C-46: Promotion creates at most one confirmed booking from a waiting place.
Observable: Repeating the same vacancy event or overlapping two attempts to promote the same member produces one booking from that waiting place.
Source: implied: U-6 and U-7 must not turn one wait into two bookings.

### C-47: Cancellation of a promoted booking does not restore the consumed wait.
Observable: After a promoted member cancels their booking, the member has zero active waits from the original join. The released place is considered for other waiting members. The cancelling member can join again through the ordinary waitlist action if eligible.
Source: choice: Cancelling a booking ends that booking's claim without reviving the earlier authorization.

### C-48: Allocation has no externally visible partially confirmed outcome.
Observable: If interrupted during promotion, the member has either an active wait with no resulting booking or one confirmed booking with no active wait. An independently withdrawn or ended wait remains withdrawn or ended. No confirmation of booking is shown before a booking exists.
Source: implied: U-7 and U-12 require a correct result after a partial failure.

### C-49: A failed promotion leaves available capacity recoverable.
Observable: If promotion fails before committing a booking, the place is still considered on recovery for the appropriate eligible wait, provided the session remains open. The failed attempt has used zero places.
Source: implied: U-12 requires interrupted allocation to resume.

### C-50: Allocation recovers without requiring a second vacancy event.
Observable: After the dependency returns, a place that was already released and is still bookable is allocated while the session remains open even if nobody cancels again. The allocation and recovery time limits in the deployment are unconfirmed.
Source: implied: U-12 requires recovery from the original opening.

### C-51: Failure after a booking commits does not undo that booking.
Observable: If the response, status refresh, or post-booking confirmation fails after promotion commits, the member later finds the same booking through the ordinary flow without another booking being created.
Source: implied: U-7 and U-12 preserve committed effects.

### C-52: A status read with an unknown result communicates uncertainty.
Observable: If the app cannot establish whether a requested join, leave, booking, or cancellation took effect, it shows that the result is unavailable or unconfirmed. It does not report success, refusal, or elevated availability based on that unknown result.
Source: implied: U-3 and U-7 require a reliable outcome.

### C-53: A delayed repeat of an already resolved waitlist action cannot reverse a newer action.
Observable: Replaying an identifiable earlier join after a later leave does not restore the wait. Replaying an identifiable earlier leave after a later deliberate rejoin does not remove the new wait.
Source: implied: U-4 and U-7 distinguish retrying the same action from making a new decision.

### C-54: The waitlist adds no outbound message requirement.
Observable: The member can learn that they are waiting, booked, or no longer waiting through the app. No new email, SMS, or push notification is needed to produce or establish any of those outcomes.
Source: choice: The booking flow provides the outcome without requiring a new delivery channel, subscription, or response to a message.

### C-55: Existing booking confirmations apply to promoted bookings where the app normally provides them.
Observable: A promoted member receives the ordinary confirmation associated with the booking under the app's existing confirmation policy. The policy's channels, content, and timing are unconfirmed.
Source: implied: U-5 produces an ordinary booking that should be recognizable to the member.

### C-56: The waitlist closes at the earlier of the existing booking cutoff and the scheduled session start.
Observable: Immediately before that boundary a qualified member can wait if the session is otherwise available for waiting. At the boundary and afterward zero new waits can be accepted. The waitlist's latest cutoff is 0 minutes before session start. Any earlier existing cutoff is unconfirmed.
Source: choice: The wait ends when there is no longer a useful chance to attend or when the existing booking rules close earlier.

### C-57: Cutoff comparisons follow the session's authoritative scheduled instant.
Observable: A member device using a different time zone or a fast or slow clock cannot change whether a session has reached its waitlist cutoff. The app's existing time zone and timestamp precision rules are unconfirmed.
Source: implied: U-10 needs one cutoff for everyone booking the same session.

### C-58: Reaching the cutoff ends all active waits for the session.
Observable: At or after the cutoff, a member whose wait did not yield a booking has no active waiting place even if there was no cancellation or member action.
Source: implied: U-10 requires an end for waits that did not yield a place.

### C-59: An opening processed at or after cutoff creates zero waitlist bookings.
Observable: If a place became available before cutoff but allocation did not commit before cutoff, late or retried allocation leaves the member without a promoted booking.
Source: implied: U-10 and U-12 prohibit late promotions.

### C-60: A session made unavailable for future booking ends its active waits.
Observable: Cancel, remove, or close a session to future ordinary bookings through a supported session operation. From when that change takes effect, the cancelled, removed, or closed session has zero active waits and cannot receive waitlist bookings. A cutoff also ends waits. Any other existing terminal session statuses are unconfirmed. A transient failure to read or process a session is handled as an interruption.
Source: implied: U-9 and U-10 end waits that can no longer produce a booking.

### C-61: The waitlist follows changes to the booking cutoff for the same session.
Observable: If a supported schedule change moves the cutoff while the wait is still active, the new cutoff governs that wait. If the new cutoff is already reached at the time of the change, no promotion can take effect after the change.
Source: implied: U-9 treats a change to an existing session as affecting its actual odds of booking.

### C-62: Reopening a session does not revive ended waits.
Observable: If a closed session reopens or a session is rescheduled after its waits ended, the earlier waits remain inactive. Eligible members can join afresh if the session is full and the waitlist is open.
Source: choice: Ending a wait ends its authority to book. Members can opt in again against the current session.

### C-63: Session changes affect confirmed bookings through existing session rules.
Observable: A promoted booking that took effect before a capacity change, schedule change, closure, cancellation, or removal is treated like a direct booking under the existing rule for that change. Supported operations and their exact consequences are unconfirmed.
Source: implied: U-9 preserves how the app treats confirmed bookings.

### C-64: A member can distinguish the disposition of a previous wait when they return to an accessible session.
Observable: A former wait is distinguishable as booked or no longer waiting. If the session has become inaccessible or was removed, the app may show its existing unavailable result. The inactive outcomes are promotion, withdrawal, definitive ineligibility, session closure or removal including cutoff, and retirement of the feature. A temporary processing failure is not an end state.
Source: implied: U-3, U-4, U-8 through U-10, and U-13 describe how a wait can stop.

### C-65: Ended waits authorize zero future bookings.
Observable: After promotion, withdrawal, definitive ineligibility, session closure or removal including cutoff, or feature retirement, delayed allocation for the old wait cannot produce another booking. A fresh successful join is a separate wait.
Source: implied: U-4, U-7, U-10, and U-13 require a final outcome for each wait.

### C-66: Waitlist data is available to operator roles only within existing authorized scope.
Observable: An operator authorized to inspect the applicable member and session can diagnose waitlist outcomes within that scope. A user without that scope cannot obtain waitlist data through operator access. Existing operator roles and reach are unconfirmed.
Source: implied: U-12 requires diagnosis without expanding access to member data.

### C-67: An authorized operator can determine the outcome of interrupted allocation.
Observable: For the affected session, an authorized operator can establish whether a specified member is actively waiting, confirmed, or has no active wait, and whether a bookable place is awaiting allocation. Existing or release support surfaces are sufficient.
Source: implied: U-12 requires verifying what remains to be allocated.

### C-68: The feature uses one admission and allocation policy across enabled sessions.
Observable: Operators use existing class controls for session availability, capacity, cancellation, and any supported schedule edits. The waitlist adds no per-session configuration for queue length, priority, or offer duration, and no manual promote or reorder control.
Source: choice: Automatic use of the session's existing controls satisfies the request without a new administrative workflow.

### C-69: Sessions that predate the feature start with zero waitlist entries.
Observable: Immediately after enabling waitlists for existing sessions, members have no waiting places unless they actually joined after the feature became available. A historical failed booking is not converted into a wait.
Source: implied: U-11 preserves past booking outcomes and requires an affirmative join.

### C-70: Existing bookings carry forward when waitlists are enabled.
Observable: A booking that was confirmed before activation still counts toward capacity and appears through the ordinary booking flow afterward.
Source: implied: U-11 adds waitlists to sessions with existing bookings.

### C-71: Activation makes waitlist admission and allocation available together.
Observable: The release accepts a successful join only when allocation can take responsibility for that wait, including recovery from interruption. If the deployment cannot support this across the booking routes it exposes, a new join is refused without creating a wait and existing ordinary booking remains available under its current rules where safe.
Source: implied: U-11 must not accept waits with no working path to a booking.

### C-72: Retirement ends active waits before waitlist-free booking resumes.
Observable: Before a rollback resumes ordinary booking without waitlist priority, the operator can verify zero active waits across the affected sessions. No pending wait can be silently bypassed by the previous release.
Source: choice: Closing the waits explicitly is the smallest safe rollback policy when the earlier app cannot serve them.

### C-73: Rollback preserves confirmed bookings made through promotion.
Observable: A promoted booking confirmed before rollback appears and counts in the earlier app exactly as an ordinary booking does. If the operator cannot verify this precondition, the rollback is held.
Source: implied: U-13 restores the earlier app with its actual bookings intact.

### C-74: A member can learn that their wait ended because waitlisting was retired.
Observable: During retirement, a member who checks through the available booking flow can learn that their affected wait ended and has no place unless a booking was confirmed. No new outbound channel is required for the rollback.
Source: choice: The wait's end must be visible before returning to an app that did not show waits.

### C-75: A fresh activation after rollback starts without reviving retired waits.
Observable: Enabling the feature again leaves waits ended by retirement inactive. The next new eligible join enters the current session's queue.
Source: choice: A retired wait no longer carries authority to make a booking.

### C-76: Ordinary bookings continue through the app's existing booking flow.
Observable: An eligible member can book an accessible session with a bookable place available to them using the same ordinary actions as before, subject to waitlist priority for newly available places. Existing booking entry points are unconfirmed.
Source: implied: U-1 adds a path for full sessions alongside the ordinary path.

### C-77: Existing non-capacity booking refusals remain in force for ordinary bookings.
Observable: An ordinary booking scenario refused before the feature for a non-capacity reason is still refused on the same grounds. The app's complete conditions, exceptions, and numeric limits are unconfirmed.
Source: implied: The request changes access to full sessions through waiting and leaves other booking eligibility in force.

### C-78: Existing direct-booking capacity rules remain in force.
Observable: With no applicable waitlist demand, a direct booking uses the same session capacity and place count as before. At that class's existing limit the app creates zero additional direct confirmed places. The capacities and any special capacity rules are unconfirmed.
Source: implied: The request adds a waitlist for the app's existing definition of full.

### C-79: Existing booking cancellation eligibility remains in force.
Observable: Ordinary and promoted bookings can be cancelled by the same authorized people and within the same time limit and conditions the app already applies. Existing cancellation roles, conditions, exceptions, and cutoff values are unconfirmed.
Source: implied: U-5 and U-13 preserve cancellation of confirmed bookings.

### C-80: Existing charges for confirmed bookings remain in force.
Observable: Where the app charges for a confirmed booking, promotion applies the same price and charge rules as the equivalent direct booking. Existing prices, currencies, and charging conditions are unconfirmed.
Source: implied: U-5 makes an ordinary booking.

### C-81: Joining a waitlist incurs zero new waitlist fees.
Observable: Joining, remaining on a waitlist, or leaving it does not trigger a fee for waitlist participation. Any existing charge at confirmation follows the ordinary booking rules.
Source: choice: The request gives no basis for a separate paid service.

### C-82: Existing cancellation consequences remain in force for promoted bookings.
Observable: Where cancellation ordinarily results in a charge, credit, refund, or no financial change, cancelling a promoted booking has the same result in the equivalent case. The existence, amounts, and timing of these consequences are unconfirmed.
Source: implied: U-5 uses ordinary cancellation for a promoted booking.

### C-83: Existing attendance rules remain in force for promoted bookings.
Observable: A member with a promoted booking satisfies the booking requirement for attendance or check-in on the same basis as a directly booked member, if the app supports those actions. Existing attendance conditions and timing are unconfirmed.
Source: implied: The place obtained through U-5 must be usable to attend the class.

### C-84: Existing session management permissions remain in force.
Observable: Adding a waitlist does not grant permission to change a session's capacity, schedule, booking availability, or cancellation or removal status. Which of those operations exist and which roles can use them are unconfirmed.
Source: implied: U-9 uses the existing session controls and their authorization.

### C-85: Existing bookable sessions remain discoverable through the same class booking entry points.
Observable: A member who could find an upcoming session before the feature can still find it under the same visibility rules. Existing browsing and discovery capabilities are unconfirmed.
Source: implied: U-1 adds a way to act on the classes people already find.

### C-86: Existing ordinary booking cutoff behavior remains in force.
Observable: With no applicable queue priority, the same ordinary booking attempt at a given time relative to the class is accepted or refused as before. The existing cutoff and precision are unconfirmed.
Source: implied: The request adds waiting and does not move the ordinary booking window.

### C-87: Waitlist-related storage failure cannot be reported as a successful change.
Observable: Force the persistence used by the deployed app to reject a join, leave, or allocation. The user or caller gets a failure or unknown outcome until the effect can be verified. The platform, its supported record sizes, entry counts, request sizes, and exact quotas are unconfirmed.
Source: implied: U-7 and U-12 are bound by the runtime persistence service's rule that rejected operations provide no evidence of a committed result.

### C-88: A request deadline does not decide the underlying waitlist outcome.
Observable: If the deployed runtime ends a request before an outcome is delivered, the next successful read shows the committed state. A timed-out response alone grants no extra place. The host or service imposing the deadline and its exact deadline are unconfirmed.
Source: implied: U-7 must tolerate the runtime enforcement of request deadlines independently of whether an action took effect.

### C-89: A confirmed cancellation does not require successful synchronous promotion.
Observable: If a cancellation commits but allocation cannot finish during the same request, the cancellation remains effective. The released place is handled under the same priority and recovery rules. The platform's synchronous execution capabilities, background execution availability, and timing bounds are unconfirmed.
Source: choice: Cancellation must remain effective when the deployment requires allocation to finish separately or after recovery.

### C-90: The waitlist can be enabled for production only where its required booking operations can run under the deployment's rules.
Observable: Before members can join in production, the deployed app can identify an authorized member, persist a join and its result, commit or recover one ordinary booking for an allocated place, and read back the outcome through the normal flow. The app runtime, hosting service, persistence service, identity service, required production configuration and permissions, and any external approvals are unconfirmed.
Source: implied: U-11 depends on the deployment rules that govern identity, persistence, execution, and access to the existing booking flow.
