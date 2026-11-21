## Use cases

### U-1: A member books an available place through the usual booking flow
Flow: The member opens a class occurrence with at least 1 bookable place and no eligible waiter ahead of them. They use the normal booking action and see a confirmed booking. An empty schedule still shows the existing empty state.
Source: implied: adding a waitlist for full classes leaves ordinary booking in place

### U-2: A member joins a full class to get a chance at a place
Flow: The member opens a class occurrence with 0 bookable places due to capacity. Even when nobody is waiting yet, they can join. The app tells them before they join that a place can become a booking automatically. On success they see that they are waiting. They can return later to check their status.
Source: request

### U-3: A member repeats an action to check or recover their place in the waitlist
Flow: The member revisits the occurrence, retries a join after an interrupted response, or submits from 2 sessions. They find 1 active entry for that occurrence. A member with an existing confirmed place cannot also queue for that place.
Source: implied: a member may encounter the same full occurrence more than once

### U-4: A member encounters an invalid or unavailable action and learns the outcome
Flow: A member attempts to join for a missing or invalid occurrence, for a class they cannot book for a reason other than capacity, or using a stale full-class view after room has opened. The app reports the outcome. If the occurrence has room for ordinary booking, the member can proceed using that option.
Source: implied: joining is an action against a specific occurrence whose eligibility or availability may have changed

### U-5: A member leaves the waitlist to give up their chance at a place
Flow: A waiting member leaves, then sees that they are no longer waiting. Repeating the action leaves them out of the queue. A different member cannot withdraw their entry through self-service. They can join again if the occurrence is still full and they are eligible. If a booking already resulted from their waitlist entry, they see that booking and use the usual cancellation flow if they want to give it up.
Source: implied: a member's plans can change while they are waiting

### U-6: A booked member cancels so their place becomes available under the existing rules
Flow: A booked member cancels through the normal flow, subject to the existing cancellation rules. If cancellation releases 1 place and a member is eligible on the waitlist, 1 waiting member gets a confirmed booking. With 0 eligible waiters, the place is available for ordinary booking.
Source: implied: a full class can have room again when a booked member cancels

### U-7: Waiting members receive newly available places when demand exceeds capacity
Flow: Several members are waiting for the same occurrence. As places open, the earliest eligible waiters get bookings. If there are fewer places than eligible waiters, the remaining entries stay active. The same flow works for the longest queue the app can hold.
Source: implied: more than one member may want places in the same full class

### U-8: A member competes for the last place while availability changes
Flow: Members try booking or joining at the same time, or a waiter leaves while a place opens. Each member sees the outcome of their action. A place is assigned at most once, and a completed withdrawal prevents a later assignment from that entry.
Source: implied: availability and participation can change between viewing an occurrence and acting on it

### U-9: A waiting member encounters an eligibility change or the end of an occurrence
Flow: A member who was eligible when joining becomes ineligible before a place opens. The next eligible member can receive the place. If the skipped member becomes eligible again while a place is still available, their entry can be considered again. If the occurrence is canceled or permanently closes for booking, members see that they are no longer waiting for it.
Source: implied: eligibility and the opportunity to book can change while people are waiting

### U-10: An operator adjusts a class to use its current capacity
Flow: Where capacity edits already exist, an operator changes an occurrence's capacity using the usual controls. An increase that creates bookable places allows the waitlist to advance. A reduction does not cancel existing bookings through waitlist processing. Removing or canceling an occurrence ends waiting for it.
Source: implied: the waitlist operates on the same class schedule and capacity as booking

### U-11: An operator enables or restarts the app and carries forward existing records
Flow: The operator starts the updated app with the existing booking configuration and data, or with an empty schedule. Existing full classes can accept waiters without being recreated. After a restart, previously accepted entries and confirmed bookings are still reflected in the app. If a place was released before processing was interrupted, assignment can resume.
Source: implied: existing users and class records must carry forward through deployment and restart

### U-12: An operator returns to the previous version and continues ordinary booking
Flow: The operator rolls back with the current class and booking data, including bookings confirmed through the waitlist. The previous version runs its usual booking flow. Pending waitlist entries do not turn into bookings while the previous version is running.
Source: implied: an operator may need to go back to the version before the waitlist

## Clauses

### C-1: An otherwise eligible member can join a waitlist for a full class occurrence
Observable: From the booking experience for an occurrence with 0 bookable places due to capacity, the member can choose to join the waitlist successfully.
Source: request

### C-2: The waitlist accepts its first eligible member
Observable: A full occurrence with 0 active entries accepts a join from an eligible member.
Source: implied: U-2 can happen before anyone else has joined

### C-3: An accepted join is visible as waiting
Observable: After joining succeeds, the member sees that their place in the class is pending.
Source: implied: U-2 requires the member to know whether the join succeeded

### C-4: A member can check their active waitlist status later
Observable: After leaving the booking view and returning while their entry is active, the member can tell that they are still waiting for that occurrence.
Source: implied: U-2 and U-3 involve waiting beyond the initial interaction

### C-5: Joining the waitlist does not itself confer a confirmed place
Observable: Immediately after joining an occurrence that remains full, the member has no confirmed booking from the join.
Source: implied: the request distinguishes waiting for a full class from booking a place

### C-6: A waitlist entry applies to a single scheduled occurrence
Observable: Joining Tuesday's occurrence of a class does not put the member on the waitlist for Thursday's occurrence of the same class.
Source: implied: in U-2, fullness applies to the occurrence the member selected

### C-7: A member has at most 1 active entry for the same occurrence
Observable: After repeated or simultaneous joins by the same member for the same occurrence, that member has only 1 active entry for it.
Source: implied: U-3 retries the same request for a chance at a place

### C-8: A repeated join preserves the member's existing entry
Observable: When a member with an active entry joins again, the original entry continues to count from its original acceptance.
Source: choice: retrying an accepted join should not make the member lose their place in line

### C-9: A member who already holds the requested place cannot join its waitlist
Observable: A member who already has a confirmed booking for the occurrence tries to wait for that same place and acquires no active entry for it.
Source: implied: U-3 already has the outcome for which the member would be waiting

### C-10: The app refuses a join that identifies no valid occurrence
Observable: Submitting a join with a missing, unrecognized, or invalid occurrence identifier yields a failure without creating an entry.
Source: implied: in U-4, a waitlist entry requires a real occurrence

### C-11: Existing booking eligibility rules other than capacity also govern joining
Observable: A member who would be refused a place even if one were available cannot join the waitlist while that same reason applies.
Source: implied: the request addresses refusal due to fullness in U-4

### C-12: A join does not queue the member if a place is available to them through ordinary booking
Observable: A member submits a join from a stale full-class view when they can now book normally. They acquire no waitlist entry.
Source: implied: U-4 limits the waitlist to the capacity problem described in the request

### C-13: A stale join never books a place through the ordinary booking flow
Observable: When a join arrives after an ordinary place becomes available to that member, the app does not confirm a booking from the stale join.
Source: choice: a member acting on a stale view can choose whether to take the available place immediately

### C-14: A stale join exposes that ordinary booking is now available
Observable: A member who submits a join when they could instead book normally can tell that a place is available.
Source: choice: a member acting on an old view needs the current availability to decide whether to book

### C-15: A refused waitlist action exposes its outcome to the member
Observable: When a waitlist action is refused, the member can tell that it did not succeed.
Source: implied: U-3 and U-4 require the member to know the result of the action

### C-16: A waiting member can withdraw their own active entry
Observable: After a member successfully withdraws from an occurrence's waitlist, the member sees that they are no longer waiting for it.
Source: choice: members need a way to withdraw an outstanding request when their plans change

### C-17: Repeating a withdrawal has no further effect
Observable: A second withdrawal of the same entry leaves it withdrawn.
Source: implied: U-5 repeats an action whose effect already holds

### C-18: A withdrawn member can join again if eligible for a full occurrence
Observable: After an earlier entry was withdrawn, a member who still meets the join conditions can successfully submit a new join for the occurrence.
Source: choice: a withdrawal applies to the current request for a place

### C-19: A new entry after withdrawal has a new place in line
Observable: A member who leaves and rejoins waits behind those whose active entries were accepted before the rejoin.
Source: choice: a new request takes effect when the member makes it

### C-20: A withdrawal takes effect before any later assignment from that entry
Observable: When withdrawal succeeds before a place is assigned, that entry never produces a booking.
Source: implied: U-5 and U-8 require a completed withdrawal to end the request for a place

### C-21: A waitlist withdrawal cannot cancel a confirmed booking
Observable: A member who attempts to withdraw after their place was confirmed still holds the booking.
Source: implied: U-5 distinguishes withdrawing a pending request from canceling a booking

### C-22: A waiting member can obtain a place that becomes bookable
Observable: If a full occurrence gains 1 bookable place while it has at least 1 eligible waiting member, one eligible waiter can obtain that place through the waitlist.
Source: implied: without access to freed places in U-6 or U-10, the waitlist cannot help a member attend the full class

### C-23: A newly available place goes to an eligible waiter before it goes to a new ordinary booking
Observable: If 1 place becomes bookable while an eligible waitlist entry is active, a new booking request from outside the queue cannot take that place ahead of the waiter.
Source: choice: existing waiters receive first access to places that open

### C-24: A place offered through the waitlist becomes a confirmed booking automatically
Observable: When 1 place opens for an occurrence with an eligible active entry, the selected member gets a confirmed booking without having to claim or accept the place.
Source: choice: one join action is enough to accept a place and there is no claim window to manage

### C-25: A member knows before joining that a place can become a confirmed booking automatically
Observable: Before submitting a join, the member can tell that a future assignment will create a booking without another action from them.
Source: choice: automatic confirmation should be clear when the member makes the request

### C-26: The earliest accepted active entry among eligible waiters receives the next place
Observable: If 2 eligible members join one after the other and 1 place opens, the member whose current entry was accepted first receives it.
Source: choice: acceptance order gives waiting members priority over later arrivals

### C-27: Entries accepted concurrently have a consistent priority relative to one another
Observable: If 2 concurrent joins both succeed, their relative order remains stable until either entry stops waiting or becomes ineligible for the assignment under consideration.
Source: choice: close-together joins need a stable order without prescribing how to break a tie

### C-28: The app respects existing booking eligibility at assignment
Observable: A waiting member who is ineligible when a place opens does not receive a confirmed booking while the disqualifying reason applies.
Source: implied: the waitlist in U-9 still results in an ordinary booking

### C-29: An ineligible entry does not block assignment to an eligible waiter
Observable: If the earliest waiting member is ineligible and a later waiter is eligible, the later waiter can receive the available place.
Source: choice: a place can be used by an eligible member despite an earlier entry's eligibility change

### C-30: A member who is temporarily ineligible keeps their active entry when skipped
Observable: If a waiting member is skipped due to a temporary eligibility restriction and the occurrence remains open for booking, they still have an active entry.
Source: choice: members can remain interested through a temporary eligibility change

### C-31: An active entry becomes eligible for assignment again when a temporary restriction ends
Observable: If a previously skipped member becomes eligible again while their entry is active and a bookable place remains, the waitlist can assign that place without an additional release.
Source: choice: keeping an entry through a temporary restriction lets the member receive a place when they can book again

### C-32: Waitlist assignment can fill multiple newly bookable places
Observable: If N places become bookable and at least N eligible members are waiting, N waiters can obtain a place.
Source: implied: U-7 allocates only the available places to members who can take them

### C-33: Waitlist assignment can leave seats for ordinary booking when there are fewer eligible waiters than places
Observable: If 2 eligible members are waiting when 3 places open and both members are assigned places, 1 place remains bookable by an otherwise eligible member.
Source: implied: U-7 shares the class capacity with ordinary booking

### C-34: Eligible entries that have yet to receive a place remain active
Observable: If 1 place opens for 2 eligible waiters, the eligible member who does not receive it still has an active entry.
Source: implied: U-7 involves more eligible waiters than currently available places

### C-35: With 0 eligible waiters, newly available places can be booked normally
Observable: A member eligible for ordinary booking can book a released place when there are no eligible waitlist entries for it.
Source: implied: the request adds a way to use places in full classes, and U-6 can release a place without eligible demand on the waitlist

### C-36: A confirmed assignment ends that member's active waitlist entry
Observable: Once the member receives a confirmed booking for the place, they are no longer waiting for it.
Source: implied: the member's request for a place in U-6 has been fulfilled

### C-37: Members can find a booking they received through the waitlist
Observable: After receiving a place, the member can see the confirmed booking wherever they normally see their own bookings.
Source: implied: assignment produces a booking the member needs to find

### C-38: The waitlist introduces no separate maximum number of entries per occurrence
Observable: For a class and member population the app otherwise supports, an eligible member's join cannot be refused solely because of the number of entries already on the waitlist.
Source: choice: the request supplies no limit on how many people may wait

### C-39: Concurrent actions cannot assign the same available place more than once
Observable: With 1 place bookable, concurrent actions that could consume it produce at most 1 new confirmed booking for the place.
Source: implied: U-8 shares the capacity that limits ordinary booking

### C-40: Retrying assignment cannot create a second booking from the same entry
Observable: After interruption or retry during assignment, one waitlist entry yields at most 1 confirmed booking.
Source: implied: U-8 and U-11 must still consume each waitlist request only once

### C-41: An entry stays active when an attempted assignment fails before creating a booking
Observable: If assignment fails while the member and occurrence still qualify, the member continues to appear as waiting.
Source: implied: U-11 needs an unfulfilled request to survive an interrupted assignment

### C-42: Canceling or removing an occurrence ends its active waitlist entries
Observable: A member checking an entry after the occurrence has been canceled or removed no longer sees the entry as active.
Source: implied: U-9 and U-10 remove the opportunity that members were waiting for

### C-43: Permanently closing an occurrence to booking ends its active waitlist entries
Observable: When the existing booking rules make it permanently too late to book an occurrence, members no longer see active entries for it.
Source: implied: U-9 has no remaining opportunity to assign a place after permanent closure

### C-44: The app's existing class visibility rules apply to waitlist access
Observable: A member who cannot access an occurrence under the existing class visibility rules gains no access to it through waitlist actions or views.
Source: implied: U-2 and U-4 act on the existing class schedule

### C-45: Member self-service cannot manage another member's entry
Observable: A member attempting to withdraw an entry belonging to a different member through self-service leaves that entry active.
Source: implied: U-5 manages the member's own request for a place

### C-46: Member self-service does not expose other members' waitlist identities
Observable: A regular member checking their own waitlist status is not shown the identities of other waiters.
Source: choice: a member needs their own status to use the waitlist

### C-47: Ordinary booking continues through the existing flow when a place is available for ordinary booking
Observable: A member can use the same booking actions as before for an occurrence with a place available to them through ordinary booking.
Source: implied: U-1 is outside the full-class condition targeted by the request

### C-48: The existing booking limit governs the availability of places
Observable: An occurrence with configured capacity N has 0 bookable places due to capacity once N places are counted against that limit.
Source: implied: U-2 and U-10 use the same capacity as ordinary booking

### C-49: Pending waitlist entries do not consume class capacity
Observable: Creating an active waitlist entry changes the number of places counted against the occurrence's capacity by 0.
Source: implied: U-2 requests a chance at a place while U-6 depends on a later place release

### C-50: Existing cancellation rules apply to bookings obtained through the waitlist
Observable: A member with a booking from the waitlist can cancel under the same conditions as a member with an otherwise equivalent ordinary booking.
Source: implied: U-5 and U-6 concern confirmed places in the existing booking app

### C-51: Adding the waitlist preserves the existing cancellation rules for ordinary bookings
Observable: An existing ordinary booking is cancelable under the same conditions before and after the waitlist is introduced.
Source: implied: U-6 changes who can take a released place

### C-52: A capacity edit uses the existing operator controls where they are available
Observable: Where an operator can currently edit capacity, the same edit is effective for how many places can be assigned through the waitlist.
Source: implied: U-10 adjusts capacity for the same occurrence used in ordinary booking

### C-53: The waitlist itself does not cancel confirmed bookings after a capacity reduction
Observable: Reducing the capacity of an occurrence with confirmed bookings triggers no cancellations from waitlist processing.
Source: implied: U-10 affects future availability via the waitlist

### C-54: An empty schedule retains its existing empty behavior
Observable: With 0 class occurrences, the booking app still opens and shows its existing empty-schedule state.
Source: implied: U-1 and U-11 may encounter an empty schedule

### C-55: Enabling the waitlist requires no new operator setting
Observable: Starting the updated app with a working existing booking configuration lets members join eligible full occurrences without an operator configuring the waitlist.
Source: choice: the requested behavior applies wherever existing class capacity makes an occurrence full

### C-56: Existing occurrences remain usable after the update
Observable: An occurrence created before the update is still available through the same class access rules, without an operator recreating it.
Source: implied: U-11 carries forward the existing schedule

### C-57: Existing confirmed bookings retain their status after the update
Observable: A booking confirmed before the update remains confirmed when its member returns after the update, absent an ordinary event that changes it.
Source: implied: U-11 carries forward current bookings

### C-58: Existing full occurrences support the waitlist upon update
Observable: An otherwise eligible member can join a still-full occurrence created before the update.
Source: implied: the request applies to full classes that already exist in U-11

### C-59: Active waitlist entries survive an ordinary restart
Observable: After restarting the updated app with the same data, a member still sees an active entry accepted before restart if it has not been fulfilled or ended.
Source: implied: U-11 carries forward pending member requests

### C-60: Existing precedence between active entries survives an ordinary restart
Observable: When 2 members were waiting before restart and both remain eligible afterward, the member who had precedence before restart has precedence afterward.
Source: choice: restarting should not change the queue order members rely on

### C-61: Confirmed bookings obtained through the waitlist survive an ordinary restart
Observable: A member whose booking was confirmed through the waitlist still sees it confirmed after restart if no ordinary event changed it.
Source: implied: U-11 carries forward confirmed bookings

### C-62: Interrupted assignment resumes after the app recovers
Observable: If an occurrence has a bookable place and an eligible entry after recovery, a member can receive that place through the waitlist without anyone making another seat available.
Source: implied: a restart or interrupted transition in U-11 must not strand a place already released

### C-63: The previous version can operate on the current class data after rollback
Observable: After the operator returns to the previous version, existing occurrences are still available under that version's ordinary class access rules.
Source: implied: U-12 requires the previous version to continue serving the current schedule

### C-64: Confirmed bookings remain valid after rollback
Observable: In the previous version, members still hold confirmed bookings from before rollback, including those obtained through the waitlist, absent an ordinary event that changes them.
Source: implied: U-12 requires the previous version to carry forward confirmed bookings

### C-65: Rollback stops waitlist assignment while the previous version is active
Observable: Releasing a place while the previous version is active does not turn a pending entry into a booking.
Source: implied: U-12 returns the app to its pre-waitlist behavior

### C-66: A pending entry cannot prevent ordinary booking after rollback
Observable: In the previous version, a member who is eligible to book an available place can book it even if a waitlist entry for that occurrence was pending at rollback.
Source: implied: U-12 restores ordinary booking in the previous version
