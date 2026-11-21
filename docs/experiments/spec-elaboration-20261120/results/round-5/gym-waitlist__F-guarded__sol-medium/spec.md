## Use cases

### U-1: A member joins a full class’s waitlist to remain in contention for a seat
Flow: The member opens a scheduled class with zero available seats, chooses to join its waitlist and sees that they are waiting for that occurrence.
Source: request

### U-2: A member books a class with availability to reserve a seat
Flow: The member opens a scheduled class that has a seat available to book, uses the existing booking flow and sees the booking outcome.
Source: implied: the request adds a path for full classes to an existing booking app

### U-3: A waiting member gets a booking when a seat becomes available
Flow: A booking cancellation releases one seat. The waiting member checks the class or their bookings and can see the resulting booking if selected.
Source: implied: a waitlist must give people a route from a full class to a seat

### U-4: A waiting member leaves the waitlist to stop being considered
Flow: The member opens their waitlisted class, chooses to leave and sees that they are no longer waiting.
Source: implied: a member can change their mind before getting a seat

### U-5: A member revisits or retries joining to check whether the first attempt succeeded
Flow: The member looks up the same occurrence after a refresh, another session or a lost response. They can determine whether they are waiting or already have a booking.
Source: implied: joining has an outcome that survives the original screen

### U-6: A member receives a refusal when a waitlist action cannot apply
Flow: The member tries an action for an unknown class, a class that has closed or a class for which they lack permission. The app shows a failure and leaves their bookings and waitlist participation consistent.
Source: implied: booking actions require a valid accessible occurrence

### U-7: An existing booker cancels to give up their seat
Flow: The booker cancels their confirmed booking through the existing app. The app reports the cancellation, and a genuinely released seat can go to a waiting member.
Source: implied: a full class commonly becomes available through an existing cancellation

### U-8: A member checks a waiting entry when the class can no longer take bookings
Flow: The class reaches its booking cutoff or is canceled. The member returns to the occurrence and can tell that their waitlist no longer offers a path to a seat.
Source: implied: the waitlist has a finite lifetime for each occurrence

### U-9: An operator rolls out the waitlist for existing scheduled classes
Flow: The operator releases the updated app with future classes and bookings already present. Members use the waitlist for eligible full occurrences and can still access existing bookings.
Source: implied: the request adds the waitlist to a running booking app

### U-10: An operator recovers seat assignment after service interruption
Flow: The app records a cancellation and then loses the ability to assign the seat. After recovery the operator can check the affected class and members can see the settled outcomes.
Source: implied: cancellation and assignment can be interrupted

### U-11: An operator rolls back the release while safeguarding current bookings
Flow: The operator stops new waitlist admissions for a planned rollback and lets active entries resolve. The earlier app version then continues to serve confirmed bookings.
Source: implied: a running app may need to return to the previous release

### U-12: A member joins a class that already has many people waiting
Flow: The member joins an otherwise eligible full occurrence with a long queue. They see their own entry and the queue continues to serve openings within the class’s actual capacity.
Source: implied: a popular class may attract many more requests than it has seats

### U-13: A member distinguishes recurring sessions to join the intended class
Flow: The member views two scheduled sessions in a series, joins one full session, then checks both sessions to see which one they joined.
Source: implied: U-1 refers to the scheduled occurrence that has no seats

### U-14: A returning member joins again after leaving to be considered for a new opening
Flow: The member leaves a queue, then makes a new join while the occurrence remains full and eligible. They see a new waiting outcome.
Source: implied: U-4 can be followed by another attempt to book the same full occurrence

### U-15: A member checks what joining authorizes before committing to the waitlist
Flow: Before joining a full occurrence, the member checks what can happen when a seat opens and chooses whether to join.
Source: implied: joining the waitlist can have a later booking consequence

### U-16: Two members join or book at the same time to compete for places
Flow: Two distinct members join the same full occurrence at once. A seat then opens as another member attempts direct booking. The app settles the outcomes without assigning the same seat twice.
Source: implied: U-1, U-2 and U-3 can occur together

### U-17: A waiting member leaves as a seat opens to avoid an unwanted booking
Flow: The member submits a withdrawal while another member’s cancellation opens a seat. The app shows whether the member left or already holds the booking.
Source: implied: U-3 and U-4 can occur together

### U-18: An operator changes an occurrence to reflect seating or schedule changes
Flow: Through existing controls where available, the operator changes capacity, reschedules or cancels the occurrence. The class and member booking status reflect the resulting waitlist behavior.
Source: implied: an existing app can change scheduled occurrences while people are waiting

### U-19: A waiting member no longer qualifies when a seat opens
Flow: A previously eligible member loses booking eligibility. A seat opens, and the app evaluates their current eligibility before assigning a seat.
Source: implied: circumstances can change between U-1 and U-3

### U-20: A member retries after an ambiguous response to resolve their status
Flow: The join or withdrawal response is lost, then the member refreshes or repeats the action. The app reflects one outcome for the intended entry.
Source: implied: U-5 and U-10 include incomplete responses

### U-21: A member checks the outcome after the app times out
Flow: The member submits a join, gets a timeout, then returns while the occurrence is still available to check whether the join took effect.
Source: implied: U-20 has to work across request and service failures

### U-22: A waiting member returns after a seat opens to check what happened
Flow: The member joins, signs out and closes the app. A seat opens before the cutoff. The member returns to check the outcome.
Source: implied: a member may be away from the app between joining and the next opening

### U-23: An operator checks a full class to investigate a member’s report
Flow: Using authorized operational access, the operator looks up the occurrence, checks the member’s waitlist outcome and distinguishes an unresolved assignment from confirmed booking or closure.
Source: implied: U-10 requires enough visibility to diagnose interrupted work

### U-24: A member keeps a booking made before waitlists were enabled
Flow: The member opens the app after rollout, finds their booking and can cancel it where the existing rules allow.
Source: implied: adding a waitlist preserves the existing booking flow

### U-25: A member books after the last waiter leaves to use the newly available seat
Flow: Once a vacancy exists and the last active entry is gone, the member books through the ordinary flow.
Source: implied: U-2 continues after the queue empties

### U-26: A member with a stale class view checks what the app can accept now
Flow: The member opens a full occurrence and keeps the page open while availability changes or the cutoff passes. When they submit the join, the app uses the current state and shows the outcome.
Source: implied: U-1 relies on an occurrence that is currently full and open

### U-27: A member returns after canceling an automatic booking to check current participation
Flow: The member cancels the confirmed booking through the ordinary flow. Revisiting the occurrence shows their current status. If the class is again eligible and full, the member can choose to join anew.
Source: implied: U-3 can be followed by U-7 for the same occurrence

### U-28: A member loses the last open seat to another booking and uses the waitlist
Flow: The member starts ordinary booking while one seat appears open. Another booking takes that seat first. The member sees the full-class result and can opt into waiting if still eligible.
Source: implied: the request applies as soon as a class is full

### U-29: An operator cancels a planned rollback to reopen new waitlist admissions
Flow: After suspending admission for a planned rollback, the operator cancels the rollback. A member can again join a qualifying full occurrence.
Source: implied: U-11 can be reversed before the earlier version takes over

### U-30: A member stays in line when a particular opening is unavailable to them
Flow: Where existing booking rules reserve a seat for a group, the first waiting member cannot use that seat. A later eligible member can receive it, and the first member remains eligible for their next qualifying opening.
Source: implied: U-3 works with existing seat access rules

## Clauses

### C-1: An eligible member can join a waitlist for a full scheduled class occurrence.
Observable: Open an eligible occurrence with zero available seats and join it. The app reports successful waitlist entry for that occurrence.
Source: request

### C-2: A waitlist entry gives a member a way to obtain a seat that opens in that occurrence.
Observable: Join a full occurrence as its sole eligible waiter. Free one seat before booking closes and observe that the member can secure that seat through the waitlist.
Source: implied: U-3 gives full-class members access to newly available seats

### C-3: A waiting member can withdraw their own entry.
Observable: Leave an active waitlist entry before a seat is assigned. The member’s current class status no longer shows an active waitlist entry.
Source: implied: U-4

### C-4: A class with a seat available for ordinary booking still supports direct booking.
Observable: Open an occurrence with a seat available for ordinary booking, then book through the existing flow and observe the normal confirmation.
Source: implied: U-2

### C-5: Joining a waitlist creates no confirmed booking by itself.
Observable: Join a full occurrence with zero seats. Only waiting status is shown for the member while no seat has been assigned.
Source: implied: U-1 distinguishes waiting from booking

### C-6: A member can determine their own active waiting status after returning to the app.
Observable: Join a full occurrence, leave the screen and return in another session as the same member. The occurrence still shows that the member is waiting.
Source: implied: U-5

### C-7: A request for an unknown occurrence creates zero waitlist entries.
Observable: Submit a join for an identifier that does not resolve to a scheduled occurrence. The action fails and no active entry appears for that member.
Source: implied: U-6 requires an actual scheduled occurrence

### C-8: The existing cancellation outcome remains available to a confirmed booker.
Observable: Cancel under the existing booking rules with people waiting. The original booker sees the ordinary cancellation outcome.
Source: implied: U-7

### C-9: An occurrence with booking permanently closed has zero active waitlist entries.
Observable: Check active participation after the waitlist cutoff, occurrence cancellation or occurrence removal. Zero entries remain active.
Source: implied: U-8

### C-10: Waitlist participation applies to already scheduled eligible occurrences at rollout.
Observable: Open an eligible full occurrence created before rollout. Its waitlist can accept an eligible member.
Source: implied: U-9

### C-11: An interrupted release of a seat can still be processed after service recovers.
Observable: Interrupt assignment after a successful cancellation. Restore service while the occurrence remains eligible and observe the waiting member’s opportunity to receive the seat.
Source: implied: U-10

### C-12: Previously confirmed bookings survive a planned release rollback.
Observable: Compare bookings immediately before and after a rollback without intervening member or operator booking actions. The same confirmed bookings are still visible.
Source: implied: U-11

### C-13: An occurrence has no separate product limit on the number of active waitlist entries.
Observable: For any finite number of already waiting members that the app can serve, another distinct eligible member can join without a refusal based on queue length.
Source: choice: the request specifies no queue cap and a cap would turn away otherwise eligible members

### C-14: Waitlist participation is scoped to exactly one scheduled class occurrence.
Observable: Join one session of a recurring class. A different session of the same class shows zero entries for that member unless they join it independently.
Source: implied: U-13

### C-15: A waitlist action requires the app to resolve the acting member’s identity.
Observable: Attempt a waitlist action without an authenticated member identity. The app does not show a successful action or change any member’s participation.
Source: implied: U-4 and U-5 require ownership across sessions

### C-16: Joining requires permission to access the occurrence through the existing booking app.
Observable: Try to join with a member account that cannot access the occurrence under current class visibility rules. Zero entries are created.
Source: implied: U-6

### C-17: Joining is available only while the member satisfies all existing ordinary booking eligibility rules other than seat availability.
Observable: For each currently enforced member eligibility check, fail that check on an otherwise joinable full occurrence. The app refuses the join. The app’s complete list of eligibility checks and any numeric thresholds are unconfirmed in the supplied workspace.
Source: choice: a seat shortage is the condition the waitlist is meant to address

### C-18: Joining is available only while a booking could otherwise be made for the occurrence.
Observable: Try joining before the existing booking window opens, after it closes or while the occurrence is unavailable to bookings under the existing rules, if those restrictions exist. Each applicable restriction refuses the join. The app’s booking window and any additional occurrence restrictions are unconfirmed.
Source: choice: waitlist availability follows the bookable window so that it serves the same class booking process

### C-19: A member with a confirmed booking for an occurrence cannot join its waitlist.
Observable: Try joining the same full occurrence that the member already booked. The confirmed booking remains the member’s current status and there is no active waitlist entry.
Source: implied: U-1 only benefits a member without a seat in that occurrence

### C-20: A member can have at most one active waitlist entry per occurrence.
Observable: Make repeated joins under the same account for one occurrence. At most one active entry can be seen for that member through any session.
Source: implied: U-5

### C-21: A join for an occurrence with a seat available to ordinary booking creates zero waitlist entries.
Observable: Select or submit a stale join for an occurrence whose seat is available to book directly. The attempted join creates zero new entries.
Source: choice: direct booking is the existing path when capacity is available

### C-22: An active waitlist entry can be inspected only by its member or an operator with applicable permission.
Observable: Try to read an entry for another member through ordinary member access. Their waiting status is not disclosed. An authorized operator can inspect the entry for support where operator access applies.
Source: implied: U-4 and U-10 distinguish member and operator access

### C-23: A member can withdraw only their own entry through member-facing waitlist actions.
Observable: Attempt a withdrawal as a different account. The entry remains active for its owner.
Source: implied: U-4

### C-24: A new join after a successful withdrawal creates a new entry if the occurrence is still eligible and full.
Observable: Leave successfully, then deliberately join again during the booking window while direct capacity is exhausted. Observe active waiting status again.
Source: choice: allow U-14 without preserving a surrendered place

### C-25: A successfully assigned seat becomes a confirmed booking automatically.
Observable: Join a full occurrence, release a seat with this member selected and still eligible, then inspect their bookings. The confirmed booking is present without a separate acceptance action.
Source: choice: U-15 avoids losing newly opened seats to unclaimed offers

### C-26: The join control discloses automatic booking before the member consents.
Observable: Open a joinable full occurrence and inspect the join action before submitting. It communicates that a seat can become a confirmed booking automatically.
Source: choice: the member needs to understand what starting U-15 authorizes

### C-27: The join control makes the ordinary booking terms applicable to automatic assignment available before consent.
Observable: Inspect a full occurrence before joining. Any booking terms the app normally presents for that occurrence are available, including applicable charges, credit use and cancellation terms where they exist. The baseline terms and their numeric amounts are unconfirmed.
Source: choice: automatic assignment should carry the known obligations of an ordinary booking

### C-28: Joining alone has zero ordinary booking charges or credit debits.
Observable: Join a full class that would consume a credit or charge on confirmed booking, if such accounting exists. While still waiting, the balance and booking charges have not changed because of the join.
Source: choice: ordinary booking obligations begin with a booking

### C-29: A confirmed waitlist booking can be found in the ordinary booking view.
Observable: After assignment, look where the member normally finds their confirmed bookings. The booked occurrence is visible there.
Source: choice: in-app booking status is sufficient to deliver the outcome

### C-30: Waitlist outcomes require no external member notification channel.
Observable: Perform a join, withdrawal, assignment and closure with no new email, text or push delivery configured. The member can verify each outcome in the app.
Source: choice: in-app outcomes fulfill the waitlist request without adding separate delivery requirements

### C-31: An occurrence’s waitlist status for its member distinguishes waiting, booked and no longer waiting.
Observable: Observe an active entry, a successful assignment and an ended unassigned entry in otherwise equivalent occurrences. Each displays its respective outcome when the occurrence is accessible. The ended outcomes are member withdrawal, definitive ineligibility or booking closure. Booking closure occurs at the waitlist cutoff, on occurrence cancellation or on occurrence removal. A booking obtained through another path shows the current booked status.
Source: choice: these outcomes communicate everything needed to act on the entry

### C-32: An inaccessible occurrence continues to follow the app’s class visibility rules when a member checks a past waitlist outcome.
Observable: After ordinary access to an occurrence is removed, try to read the outcome through a saved waitlist link. The link does not reveal details protected by current class visibility rules.
Source: implied: U-5 applies to the member’s authorized view

### C-33: Waitlist action feedback tells the member the outcome when it is known.
Observable: Submit a successful action, a refused action or an action whose outcome cannot yet be confirmed. The member can distinguish accepted, refused and uncertain feedback. A refusal for lack of access can use the same feedback as an unknown occurrence.
Source: choice: outcome feedback supports safe retry without exposing occurrence existence

### C-34: Automatic assignment of a vacancy prioritizes eligible active entries that can use it by their acceptance order.
Observable: Join as member A, then as member B. While both qualify, release one seat and observe A receive it. If two accepted joins cannot be distinguished by time, the app still settles on one order for those entries and uses it consistently.
Source: choice: first accepted, first served gives waiting members predictable priority without requiring a public rank

### C-35: Rejoining after withdrawal takes priority from the new acceptance.
Observable: A joins, B joins, then A withdraws and joins again. With both eligible, one opening goes to B.
Source: choice: withdrawal surrenders the previous place

### C-36: Each newly available seat can be filled through the active waitlist while an eligible member can use it.
Observable: Release one or more seats by a confirmed booking cancellation or a capacity increase, where supported. While booking is open, each new seat can go to one waiting member until the openings or eligible entries run out.
Source: implied: U-3 applies whenever the occurrence has capacity for more bookings

### C-37: A vacant seat is unavailable to ordinary direct booking while it is due for waitlist assignment.
Observable: With one eligible active entry and one vacancy, attempt to book as a different member before assignment has settled. The direct attempt cannot take that seat.
Source: choice: U-16 gives the queue priority over new arrivals

### C-38: Unused capacity returns to ordinary booking when the queue has no active member eligible to fill it and eligibility evaluation is settled.
Observable: Free two seats with one eligible waiter, and let assignment settle. Exactly one seat remains available for ordinary direct booking.
Source: choice: existing direct booking resumes for capacity the queue cannot use

### C-39: An accepted join reflects the occurrence’s state at the time the join takes effect.
Observable: Open a full occurrence, then make a seat available for ordinary booking before submitting its join action. The submitted join follows the current availability rather than the earlier screen.
Source: implied: U-1 and U-2 apply to the actual availability

### C-40: A duplicate join for an active entry retains the entry’s original priority.
Observable: A joins, B joins, then A repeats the join. With both eligible, one opening still goes to A.
Source: implied: U-5 repeats the same action on the same entry

### C-41: Repeating a join while the original entry remains active returns that waiting outcome.
Observable: Lose a join response, then repeat the action while the entry is active. The app returns waiting status for that entry.
Source: implied: U-5

### C-42: Repeating a join after an assignment has confirmed the member’s booking returns that booking outcome.
Observable: Lose a join response and let assignment complete. Repeat the join while the booking is confirmed and see the confirmed booking status.
Source: implied: U-5

### C-43: Withdrawal takes effect if it wins a race against assignment.
Observable: Submit a withdrawal that takes effect before assignment completes. The member is no longer waiting and receives zero bookings from the withdrawn entry.
Source: implied: U-17

### C-44: An already confirmed booking can be surrendered only through the ordinary booking cancellation rules.
Observable: Submit a withdrawal after the seat has already been assigned. The action reports the booked outcome. To give up the seat the member must use ordinary cancellation, with its usual eligibility and terms.
Source: choice: a waitlist withdrawal should not bypass existing cancellation rules

### C-45: A repeated withdrawal of an already withdrawn entry leaves that entry ended.
Observable: Lose the response to a withdrawal, then repeat it for that entry. The app reports the withdrawn or no longer waiting outcome.
Source: implied: U-20

### C-46: A stale withdrawal for an earlier entry cannot withdraw a later entry.
Observable: Leave, make a new join and then repeat the leave action for the earlier entry. The new entry remains active.
Source: choice: a delayed action applies to the participation the member intended to end

### C-47: Automatic assignment requires current ordinary booking eligibility.
Observable: Make a waiting member fail an ordinary eligibility check before a vacancy is assigned. No booking is confirmed for that member through the waitlist while the failure applies.
Source: choice: all seat assignments must honor the existing booking rules

### C-48: A definitive eligibility failure at assignment ends that entry with no booking.
Observable: With a vacancy open, determine conclusively that the first waiter fails a member booking eligibility rule independently of the seat’s availability. The entry ends, and that member sees the ended status when the occurrence is accessible.
Source: choice: ending an ineligible entry lets the queue move without indefinitely blocking other attendees

### C-49: A definitive booking eligibility refusal advances consideration to the next active entry for the still-available seat.
Observable: Queue A before B, make A definitively ineligible at the time of assignment and release one seat. If B is eligible, the app confirms B’s booking.
Source: choice: try to fill the vacancy while maintaining priority among eligible members

### C-50: An inconclusive eligibility check leaves the affected entry active.
Observable: Temporarily lose an eligibility dependency while evaluating the first waiter. After recovery and before any permanent closure, the entry still has its original priority if no booking was confirmed.
Source: choice: service failure is insufficient evidence to discard the member’s place

### C-51: A transient assignment failure leaves that vacancy awaiting the same priority order.
Observable: Interrupt the first eligible assignment before it takes effect. While the vacancy remains and booking stays open, a later waiter or direct booker cannot receive that vacancy ahead of the unresolved earlier entry.
Source: choice: temporary failure should not silently change seat priority

### C-52: An occurrence can never gain a booking from the waitlist above its current capacity.
Observable: For capacity N, start with N confirmed bookings, cancel one and trigger overlapping assignment attempts. At most one new booking is confirmed for the single vacancy. If a permitted capacity edit leaves confirmed bookings above N, no additional booking is confirmed while occupancy is at least N. The app’s permitted capacity range is unconfirmed.
Source: implied: the request addresses full classes without exceeding their capacity

### C-53: An assignment uses the capacity that applies when the booking takes effect.
Observable: Release one seat, then reduce the occurrence’s capacity to the number of existing bookings before assignment completes. There is no newly confirmed booking while capacity is exhausted.
Source: implied: U-18 can meet U-3

### C-54: A capacity reduction does not itself end active waitlist entries unless the occurrence permanently closes to booking.
Observable: Reduce capacity, leaving zero seats and booking otherwise open. Existing eligible entries remain active in their prior order.
Source: choice: queue membership is useful if seats can open again

### C-55: A confirmed booking can result at most once from a given waitlist entry.
Observable: Repeat seat-opening processing or retry after a lost assignment result. For the entry there is at most one confirmation, even if the resulting booking has since been canceled.
Source: implied: a queue entry is a single chance to get a seat

### C-56: An assignment reports booked only when the ordinary booking took effect.
Observable: Interrupt assignment before a confirmed booking exists. The member sees no confirmed outcome for the interrupted attempt.
Source: implied: U-10 requires truthful status

### C-57: A confirmed assignment ends the active waitlist entry for that occurrence.
Observable: Let assignment succeed and refresh waitlist status. The member is booked with zero active entries for that occurrence.
Source: implied: U-3 resolves the member’s need to wait

### C-58: An ordinary booking obtained by a waiting member ends their own active entry for that occurrence.
Observable: If a permitted existing booking path can give an active waiter a booking for the same occurrence, complete that booking and check the waitlist. The member is no longer waiting.
Source: implied: there is no need to wait after obtaining a seat in U-3

### C-59: Canceling a confirmed booking creates zero automatic waitlist entries for the member who canceled.
Observable: Cancel a booking originally obtained through either booking path. The member has zero active entries unless they deliberately join again.
Source: choice: cancellation ends the booking without renewed consent to join

### C-60: Automatic assignment confirms zero bookings after the occurrence permanently closes to booking.
Observable: Delay assignment until booking permanently closes. The delayed attempt produces zero confirmations for the closed occurrence.
Source: implied: U-8 ends the chance to secure a seat

### C-61: A member can have at most one confirmed booking for the same occurrence when using the waitlist.
Observable: Race assignment against another valid booking path for the same member and occurrence. At most one confirmed booking for the member results.
Source: implied: the waitlist gives a member a seat in the occurrence once

### C-62: A vacancy is reconsidered after a successful withdrawal of an unresolved earlier entry.
Observable: Make the first entry wait on a recoverable problem while a vacancy exists. Withdraw it successfully. The next eligible entry can obtain the vacancy while the occurrence is open.
Source: choice: a withdrawn entry cannot continue holding up someone else’s chance

### C-63: A runtime request timeout leaves the outcome checkable from a fresh member session.
Observable: Force the deployed platform’s request deadline during a join or withdrawal. Reopen the occurrence and inspect the current status or retry the same action. The app can resolve whether the original action took effect. The deadline and its scope are unconfirmed because the runtime is unidentified.
Source: implied: U-21 under the platform’s request execution deadline

### C-64: An assignment can finish without a live member session.
Observable: Sign out of all member sessions after joining. Open a seat before the cutoff and later sign in to see the confirmed booking for the eligible member. The runtime’s limits on work after a request ends are unconfirmed.
Source: choice: U-22 requires assignment independent of a member session because a runtime may end request work when that request terminates

### C-65: A runtime execution interruption cannot permanently strand an eligible vacancy while service is healthy and the occurrence remains bookable.
Observable: Interrupt assignment at the platform’s execution boundary, then restore service before booking closes. The active queue can still fill the vacancy without another cancellation, operator action or member visit. The execution duration cap and recovery interval are unconfirmed.
Source: choice: U-10 must recover even when the execution platform stops work before it finishes

### C-66: A platform-rejected join cannot be reported as accepted without a recorded entry.
Observable: Submit a join for a member with no active entry and cause a request-size, validation or service-quota rejection that prevents it from taking effect. The member sees a failed or uncertain action, then finds zero active entries for that attempt after refreshing. The platform’s request size and rate limits are unconfirmed.
Source: implied: U-5 under platform request acceptance and quota enforcement

### C-67: A capacity or quota failure while saving a state change leaves the last completed state visible.
Observable: Exhaust a deployed storage limit while a join, withdrawal or assignment is being recorded. After recovery the member sees the last effective outcome unless the whole requested change took effect. Storage and transaction limits are unconfirmed because the storage platform is unidentified.
Source: implied: U-10 and U-20 under the storage service’s acceptance limits

### C-68: Occurrence cutoff decisions use the booking service’s effective time.
Observable: Change a member device’s clock or time zone and attempt an action after the actual cutoff. The result is the same as from a correctly set device. Deployment clock precision and the app’s cutoff time zone are unconfirmed.
Source: choice: the booking cutoff must apply consistently despite independent device clocks

### C-69: The waitlist is usable in production only when the deployed app can enforce normal member authentication.
Observable: In the production environment, use a valid existing member session to join, then attempt the same action without an accepted session. Only the authenticated account can get an entry. The runtime’s production authentication prerequisites are unconfirmed.
Source: implied: U-9 under the app platform’s production identity requirements

### C-70: The waitlist is usable in production only when the production booking environment can durably retain accepted outcomes.
Observable: In the production environment, join an eligible full occurrence and check the outcome after a session or process restart. The accepted entry remains available for assignment. The runtime’s production persistence prerequisites and quotas are unconfirmed.
Source: implied: U-9 under the requirement that production state survive runtime restarts

### C-71: The waitlist can operate in an environment with no newly approved outbound notification service.
Observable: Enable the waitlist in an otherwise functional deployed app without new email, SMS or push credentials or approvals. Joining and automatic booking still work through the app. Any separate host-specific production rollout requirements remain unconfirmed.
Source: choice: in-app delivery avoids dependence on outbound service configuration or platform approval

### C-72: Existing confirmed bookings remain confirmed when the waitlist is enabled.
Observable: Compare a class’s bookings immediately before and after enabling the release, with no intervening class or booking actions. Each preexisting booking remains confirmed for the same member and occurrence.
Source: implied: U-24 adds a queue without disturbing booked seats

### C-73: Existing scheduled occurrences retain their original scheduling details during rollout.
Observable: Compare each occurrence’s class identity and scheduled start before and after rollout with no operator edits. The values match. The app’s additional scheduling fields are unconfirmed and retain their existing values where present.
Source: implied: U-9 introduces waitlist behavior for the same scheduled occurrences

### C-74: Enabling the waitlist creates zero entries for historical failed bookings.
Observable: Enable the waitlist after one or more members previously tried to book a full occurrence. Those members see no active entry unless they join after rollout.
Source: choice: joining requires the current member’s deliberate consent

### C-75: Ordinary direct booking retains its existing member eligibility rules.
Observable: For each baseline eligibility rule, compare direct booking before and after enabling the waitlist on an occurrence with capacity available for ordinary booking. The same cases qualify or fail. The exact rule list and numerical thresholds are unconfirmed.
Source: implied: U-2 preserves the existing direct booking flow

### C-76: Ordinary cancellation retains its existing eligibility rules.
Observable: Try to cancel a direct or waitlist-originated booking under each existing cancellation eligibility rule. The result follows the same rules used for bookings before the update. The complete conditions, including any cancellation deadline, are unconfirmed.
Source: implied: U-7 preserves ordinary cancellation

### C-77: Ordinary cancellation retains its existing financial terms.
Observable: Cancel a booking obtained through the waitlist in circumstances in which an ordinary booking receives a fee, refund or returned credit, where supported. The same terms apply. The policies and amounts are unconfirmed.
Source: choice: automatic bookings are ordinary confirmed bookings

### C-78: An automatic booking uses the ordinary booking’s applicable financial terms.
Observable: Compare successful direct and automatic bookings for equivalent eligible members in the same occurrence. Any applicable charge or credit debit follows the pricing and entitlement rules that apply to an ordinary booking for which the member has given equivalent consent, whose complete list and figures are unconfirmed.
Source: choice: joining creates a route to the same booking

### C-79: A retried automatic assignment cannot repeat an ordinary booking charge or debit.
Observable: Where the app charges or debits for a booking, interrupt or retry one automatic assignment around confirmation. At most one successful charge or credit debit for that booking remains.
Source: implied: U-10 and U-20 preserve the financial effect of a single booking

### C-80: An automatic assignment that ultimately fails leaves no completed booking charge or debit for that attempt.
Observable: Interrupt an automatic booking before it succeeds in circumstances where ordinary booking has a charge or credit debit. Once the failure settles, the member has zero completed charges or debits for that failed attempt.
Source: implied: U-10 leaves no orphaned financial effect

### C-81: Enabling the waitlist preserves the configured capacity of each occurrence.
Observable: Enable the release with a class of capacity N. With no operator capacity change, the class still has capacity N.
Source: implied: U-9 applies the queue to the seats already configured

### C-82: An active waitlist entry consumes zero seats.
Observable: Fill an occurrence of capacity N with N confirmed bookings, add waiting members, then release one seat. The waiting entries themselves add zero to the count of confirmed bookings.
Source: implied: U-1 provides waiting without granting a seat

### C-83: Existing class discovery and access restrictions continue to govern discovery and access through the waitlist.
Observable: Compare whether each account can find or open the same occurrence before and after rollout, including accounts without a signed-in identity and accounts without permission. Access and visibility follow the baseline rules, whose complete access conditions are unconfirmed.
Source: implied: U-6 and U-9 preserve class access

### C-84: Ordinary cancellation releases capacity only if it actually ends a confirmed booking.
Observable: Submit a refused, duplicate or interrupted cancellation that leaves the number of confirmed bookings unchanged. Zero additional seats become available as a result of that attempt.
Source: implied: U-7 requires a genuinely released seat

### C-85: An empty queue leaves all otherwise bookable vacancies available to ordinary booking.
Observable: Open a seat when an occurrence has zero active entries. The seat is accessible to ordinary booking under the existing rules.
Source: implied: U-25

### C-86: Ordinary direct bookings respect the existing occurrence capacity constraint.
Observable: Race ordinary bookings for one seat that is available to direct booking. At most one direct booking confirms for the seat.
Source: implied: a full class in the request has no further seats available to book

### C-87: Members see no other member’s waitlist identity or participation through member access.
Observable: Join as one member and inspect the same class as another. The second account sees no other member’s names, account identifiers or individual waitlist outcomes, including in refusals.
Source: implied: U-4 and U-5 describe self-service for one’s own entry

### C-88: An authorized operator can determine the waitlist outcome for a specified member and occurrence.
Observable: Using the deployment’s authorized operational access, look up the pair and determine the most recent waitlist outcome where available, drawn from no entry, active, booked from the entry, withdrawn, ended for definitive ineligibility, ended at booking closure, or ended because the member booked through another path. No separate operator interface is required.
Source: choice: U-23 requires diagnosis without expanding member-facing features

### C-89: An authorized operator can distinguish a vacancy awaiting assignment from a settled absence of an eligible waiter.
Observable: Check an occurrence with an unresolved assignment failure, then check an occurrence whose queue is empty. The two cases are distinguishable through authorized operational access.
Source: choice: U-10 requires a way to tell whether work remains after a disruption

### C-90: Operator access for waitlist inspection follows the existing authorization boundary for operational booking data.
Observable: Attempt operational inspection as a member without permission and as a permitted operator. Only the authorized operator can read other members’ outcomes. Existing operator roles are unconfirmed.
Source: implied: U-23 grants access only within existing permissions

### C-91: Waitlist priority has no operator override in the waitlist feature.
Observable: Inspect the available waitlist actions. The feature has no action to move an entry ahead of another, promote a selected waiter out of sequence or alter the order of accepted entries.
Source: choice: ordinary queue operation and recovery do not require a manual priority feature

### C-92: A planned rollback can suspend new waitlist admissions before the earlier release is restored.
Observable: Set the deployment to drain the waitlist before restoring the previous version. A member who would otherwise be eligible cannot create a new entry and can tell admissions are unavailable.
Source: choice: U-11 needs a way to reach zero active entries without abandoning the people waiting

### C-93: Suspending admissions for rollback leaves existing entries eligible for assignment.
Observable: Start draining with one active entry, then release a seat before booking closes. The eligible waiter still receives the booking.
Source: choice: admissions suspension must honor existing commitments

### C-94: Suspending admissions for rollback preserves member withdrawal of active entries.
Observable: Start draining with one active entry and withdraw as its member. The member can end the entry normally.
Source: choice: existing participants retain a way to leave during rollback preparation

### C-95: Restoring a version that cannot honor waitlist entries requires zero active entries before the switch.
Observable: With at least one active entry, check the planned rollback readiness. The incompatible switch is not ready. Once the last entry ends through withdrawal, definitive ineligibility, a booking through either path, or closure at the cutoff, on cancellation or on removal, the active-entry condition is satisfied.
Source: choice: the old version should take over only when there are no unfulfilled waitlist commitments

### C-96: A rollout after rollback cannot revive already ended waitlist entries.
Observable: Resolve an entry, roll back and then restore the waitlist release. The ended entry stays inactive.
Source: implied: U-11 and U-9 preserve completed outcomes

### C-97: For waitlist admission, a class is full for an otherwise eligible member when zero seats are available to that member through ordinary direct booking.
Observable: Open a class with one configured seat but one confirmed booking. The class is full for waitlist purposes. Free the seat with no active queue and it is no longer full for waitlist purposes. A vacancy due for assignment under C-37 is excluded from direct availability.
Source: choice: members need a consistent result when a physical vacancy is already being handled for the queue

### C-98: The full-class booking surface presents an eligible member with the join action.
Observable: Use the existing member booking surface for an eligible full occurrence while admissions are enabled. The member can find and submit the join action from that booking experience.
Source: implied: U-1 requires a discoverable alternative to being turned away

### C-99: The waitlist cutoff is the earlier of the applicable ordinary booking cutoff and the occurrence’s scheduled start.
Observable: Check the occurrence immediately before the earlier instant and at that instant. With all other conditions met and the service healthy, the waitlist is open immediately before the boundary and closed at the boundary. The baseline cutoff offset is unconfirmed. If the app has no booking cutoff, the scheduled start is the boundary.
Source: choice: members wait for an upcoming class in its existing booking window

### C-100: Temporary suspension of ordinary booking leaves active waitlist entries intact.
Observable: Temporarily suspend booking where the existing app permits it, with an entry already active and the final cutoff still in the future. The entry remains active with its original priority.
Source: choice: a temporary occurrence-wide constraint can lift before the class closes

### C-101: Automatic assignment pauses while ordinary booking for the occurrence is temporarily suspended.
Observable: Release a vacancy during a temporary booking suspension. No assignment confirms during suspension.
Source: choice: the waitlist respects temporary occurrence-wide booking restrictions

### C-102: Canceling an occurrence ends its active entries.
Observable: Cancel an occurrence with active waiting members. The occurrence has zero active entries as soon as the cancellation takes effect.
Source: implied: U-8 has no remaining class to book

### C-103: Removing an occurrence ends its active entries.
Observable: Where the existing app allows removal, remove an occurrence with active waitlist entries. Authorized inspection after removal shows zero active entries for it.
Source: implied: U-18 cannot leave a queue eligible for an occurrence that no longer exists

### C-104: A reschedule that preserves an open occurrence’s identity preserves its active entries.
Observable: Move a scheduled session to a different future time using the existing reschedule behavior while keeping the same occurrence open for booking. The same waiting members retain their relative priority.
Source: choice: the queue belongs to the same occurrence across edits

### C-105: A replacement occurrence inherits zero waitlist entries from the original occurrence.
Observable: Replace a canceled or removed occurrence with a new one, even at the same time and under the same class name. The new occurrence starts with zero inherited entries.
Source: choice: consent applies to the occurrence the member joined

### C-106: Reopening an occurrence after permanent waitlist closure leaves its ended entries inactive.
Observable: Change the schedule or booking cutoff after the queue has already ended so that the occurrence can take bookings again. Previously ended entries stay inactive even when members are eligible to join anew.
Source: choice: closure is a final outcome for each entry

### C-107: Reopening before permanent closure makes current vacancies eligible for waitlist assignment again.
Observable: While bookings are temporarily suspended, create a vacancy with one eligible active waiter. Reopen booking before the cutoff without any other seat release. The waiting member can receive the seat.
Source: choice: U-3 should serve the next opening even if the seat opened during a pause

### C-108: A retry of an earlier join cannot create participation again after that entry has ended.
Observable: Join, end the entry, then replay the earlier join without opting in again. The replay creates zero new entries.
Source: choice: a delayed action cannot reapply consent after withdrawal, booking, definitive ineligibility or closure

### C-109: A newly initiated join can follow an ended entry once the member is again eligible for a full open occurrence.
Observable: End a member’s entry because eligibility failed or because the occurrence closed. When the member and same occurrence again meet all join conditions, a new deliberate join can create one active entry with new priority.
Source: choice: the old outcome is final but does not bar a fresh request for a qualifying class

### C-110: Current status never shows a canceled booking as confirmed.
Observable: Cancel a booking that came from the waitlist. On returning to the occurrence or ordinary booking view, the member no longer sees that booking as confirmed. Any available history may still show that assignment previously occurred.
Source: implied: U-7 and U-27 report current booking state

### C-111: Automatic booking requires the fulfillment of any ordinary booking prerequisite that needs fresh member action.
Observable: Use an occurrence for which ordinary booking would require a new payment approval, waiver or similar affirmative action at assignment time. If the prerequisite is unfulfilled when the seat is ready for assignment, no automatic booking is confirmed for that member. The app’s applicable prerequisites are unconfirmed.
Source: choice: consent to join cannot take the place of a separate mandatory booking authorization

### C-112: A join refusal due solely to a temporarily unavailable dependency retains any existing active entry.
Observable: Attempt a repeated join while the service cannot verify current eligibility or retrieve the response. After recovery the original active entry remains if it was not otherwise resolved.
Source: implied: U-20 retries without withdrawing

### C-113: Excess capacity beyond what the active queue can use remains available to ordinary direct booking.
Observable: Create two otherwise bookable vacancies with exactly one active entry whose assignment is pending. One vacancy remains available to ordinary booking during that pending assignment.
Source: choice: queue priority should withhold at most one seat per active entry

### C-114: A planned rollback waits for unresolved assignment outcomes to settle.
Observable: Begin rollback with an assignment whose booking, charge or credit debit outcome remains uncertain. The earlier release is not ready to take over until the outcome is settled, even if there are zero currently visible active entries.
Source: choice: U-11 must preserve booking and accounting outcomes across releases

### C-115: Malformed waitlist actions leave all participation unchanged.
Observable: Submit a join or withdrawal with a missing occurrence identifier, an invalid identifier for the deployed app, a target of the wrong kind such as a class series, or a missing entry reference when the intended withdrawal cannot be identified. The action is refused with zero changes. The existing identifier format and applicable length limits are unconfirmed.
Source: implied: U-6 requires an unambiguous scheduled occurrence or entry

### C-116: An application response that identifies the loss of the last direct-booking seat makes the waitlist available to an otherwise eligible member.
Observable: Race two direct bookers for one seat. Once the losing booker receives a full-class outcome, they can find the join action from that booking experience while admissions are open.
Source: implied: U-28

### C-117: A direct booking attempt that loses the last seat creates zero waitlist entries by itself.
Observable: Race two direct bookers for one seat. Without deliberately joining, the losing booker sees zero active entries created for them.
Source: choice: joining and its automatic booking consent require an affirmative action

### C-118: An available-seat refusal of a stale join tells the member they can use ordinary booking.
Observable: Leave the full-class view open until capacity becomes available with no higher priority commitment. Submit the stale join and see that ordinary booking is the applicable action.
Source: choice: tells U-26 how to stay in contention when availability moves in the other direction

### C-119: Automatic assignment requires the member to retain permission to book the occurrence.
Observable: Join while allowed to book, then definitively revoke that access before a seat opens. The waitlist does not confirm a booking for that member.
Source: implied: U-19 and U-6 require present authorization

### C-120: Waitlist assignment respects existing restrictions that make a seat unavailable to the next waiter.
Observable: Where the app supports seat holds or reserved capacity, place a hold or restriction on the last seat before assignment takes effect. The member gains no booking that the existing hold or restriction would forbid. The complete set of such restrictions and their duration limits are unconfirmed.
Source: choice: the waitlist provides a route to usable capacity under existing booking constraints

### C-121: A waiter whose ordinary shared booking entitlement was used elsewhere cannot receive a booking that exceeds that entitlement.
Observable: If two occurrences share a member eligibility limit or credit budget, race assignments for the same member with only one qualifying unit left. At most one consumes that unit. Existing entitlement types, limits and amounts are unconfirmed.
Source: choice: automatic assignment must enforce the same cross-occurrence eligibility checks as direct booking

### C-122: A fresh booking authorization required at assignment is a definitive eligibility failure when the member has not supplied it.
Observable: Release one seat for an entry whose booking now requires ungranted consent under the existing terms. The entry ends as ineligible when evaluated for the seat. Where the restriction applies, use the existing terms for charge, credit debit, waiver and any other authorization whose full list and thresholds are unconfirmed.
Source: choice: a seat can go to another eligible waiter instead of waiting for an authorization the feature does not collect after joining

### C-123: An assignment can use only ordinary booking terms the member has authorized.
Observable: Join under one set of terms. Change an applicable payment obligation, credit requirement or cancellation obligation before assignment. If the existing authorization does not cover the changed terms, the automatic booking does not confirm. The app’s authorization rules and thresholds are unconfirmed.
Source: choice: a waitlist opt-in authorizes the booking terms the member accepted

### C-124: A release of capacity after booking closes cannot reopen ended participation.
Observable: Repeat or deliver late a seat-opening action from before the cutoff after the cutoff has passed. It creates zero active entries for that occurrence.
Source: implied: U-8 is final for those entries

### C-125: A vacancy can return to ordinary booking after the last active entry definitively ends without a booking.
Observable: Leave one vacancy awaiting the last active waiter, then end that entry by withdrawal or definitive ineligibility while booking stays open. The vacancy becomes bookable through the existing flow.
Source: choice: an ended entry no longer has priority on open capacity

### C-126: A successful cancellation remains visible while waitlist assignment is unresolved.
Observable: Complete an ordinary cancellation when the assignment dependency is unavailable. Before the vacancy is resolved, the original booker can still observe their cancellation under the existing rules.
Source: implied: U-7 and U-10 can finish at different times

### C-127: Planned rollback can be abandoned before switching versions to restore new admissions.
Observable: Suspend admissions, then abandon rollback without switching versions. A new eligible join for a full occurrence is accepted again.
Source: choice: U-29 lets the deployment resume normal service after a reversed release decision

### C-128: An earlier app version continues to permit ordinary operations on confirmed waitlist bookings after compatible rollback.
Observable: After the rollback in U-11, open a confirmed booking originating from an assignment and use an ordinary action allowed for that booking, including cancellation under the baseline rules. The action remains available.
Source: implied: U-11 preserves a booking members can still use

### C-129: A previous no-longer-waiting outcome remains checkable while the occurrence is available for ordinary member inspection and the waitlist release is serving it.
Observable: End an entry without a booking, leave the app and return to the same accessible occurrence before starting another join. The member can verify they are no longer waiting. The app’s existing class access duration and retention obligations are unconfirmed. No separate waitlist history view is required.
Source: choice: U-5 needs a durable current outcome without adding a history product

### C-130: An entry remains active when a specific vacancy is unusable solely because of an existing restriction on that vacancy.
Observable: Where the existing app restricts seat use, release a restricted seat that the first waiter cannot use. If the waiter would qualify for an unrestricted seat and the waitlist otherwise remains open, they keep their original place.
Source: choice: lack of usable capacity for one opening is separate from losing ordinary booking eligibility

### C-131: A vacancy restricted to a subset of waiting members can be assigned to the earliest eligible waiter in that subset.
Observable: With A queued before B and a vacancy only B may use, observe that B can obtain that vacancy. With an unrestricted vacancy that either could use, the earlier active eligible entry takes priority.
Source: choice: U-30 preserves both existing seat restrictions and the acceptance order among waiters who can use a vacancy

### C-132: An existing seat restriction ending can trigger waitlist assignment without another booking cancellation.
Observable: Where a seat hold can expire or reserved capacity can be released under existing rules, release an otherwise unused seat this way while the queue is active. An eligible entry can receive the seat without a new cancellation.
Source: implied: U-3 applies once a seat is available to the member

### C-133: An active waitlist entry has no separate age-based expiration before the occurrence’s waitlist cutoff.
Observable: Leave an eligible member waiting with zero usable vacancies from their accepted join until immediately before the waitlist cutoff. The entry stays active absent member withdrawal, a booking through either path, definitive ineligibility at assignment, occurrence cancellation or removal. The waitlist adds zero age-based expiry thresholds.
Source: choice: the occurrence is the boundary that determines how long waiting can be useful

### C-134: A member can have active entries for more than one eligible occurrence at a time.
Observable: Join two different full occurrences for which the same member independently meets the join conditions. Both show active entries. The waitlist adds no cross-occurrence membership cap.
Source: choice: each occurrence has its own queue and ordinary eligibility governs eventual booking

### C-135: A second simultaneous join from the same member cannot create another place in the same occurrence.
Observable: Submit two join actions together from different sessions for one member and one full occurrence. Once both settle the member has exactly one active entry, assuming neither was refused for independent reasons.
Source: implied: U-5 and U-16 can overlap for the same member

### C-136: A current view can show a booking that took effect before cutoff even if its confirmation response arrives after cutoff.
Observable: Make the automatic booking take effect before the cutoff and delay delivery of the outcome until afterward. When the member checks, the booking is confirmed unless it was subsequently canceled under the ordinary rules.
Source: implied: U-8 closes the queue while U-10 can delay an outcome response

### C-137: Ordinary direct booking retains its existing booking window.
Observable: Compare ordinary booking immediately before opening, at opening, at the ordinary cutoff and afterward with no queue ahead of the member. Ordinary booking responds as it did before rollout. The baseline opening instant, cutoff instant and inclusion of those exact instants are unconfirmed.
Source: implied: U-2 retains the ordinary booking window

### C-138: Ordinary direct booking retains its existing financial terms.
Observable: Compare an otherwise identical ordinary direct booking before and after rollout. Any prices and applicable credit use or booking fees remain governed by the same baseline rules. The complete baseline terms and amounts are unconfirmed.
Source: implied: U-2 leaves the ordinary cost of booking in place

### C-139: Canceling an occurrence retains its existing effect on confirmed bookings.
Observable: Cancel an occurrence through the existing operator flow, with both ordinary and waitlist-originated bookings present if supported. The confirmed bookings follow the same cancellation policy used before rollout. Existing effects on booked members, including applicable refund, credit or communication rules, are unconfirmed.
Source: implied: U-18 adds queue closure to the existing class cancellation behavior

### C-140: Automatic bookings retain any existing confirmation behavior attached to ordinary bookings.
Observable: Compare the effects the existing app produces for equivalent automatic and ordinary confirmations, including existing confirmation notifications and calendar updates where applicable. The complete set of existing effects, destinations and delivery timing limits is unconfirmed.
Source: choice: an automatic booking gets the ordinary confirmation effects with no additional waitlist channel

### C-141: A failure to deliver an existing confirmation message does not create another waitlist booking.
Observable: Where the app has separate confirmation delivery, interrupt it following a completed booking and retry delivery. The member still has the one booking and zero duplicate bookings from that entry.
Source: implied: U-10 and U-20 preserve an already completed booking through a delivery failure

