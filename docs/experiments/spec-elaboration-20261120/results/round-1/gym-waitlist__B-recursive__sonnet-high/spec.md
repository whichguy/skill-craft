## Use cases

### U-1: A member joins the waitlist of a full class, to have a chance at a spot instead of being turned away
Flow: The member opens a class that is full. Where they used to meet a refusal they see an action to join the waitlist. They take it and are told they are on the waitlist, at which position, and that they will be booked automatically if a spot opens.
Source: request

### U-2: A member checks where they stand on their waitlists
Flow: The member opens their own bookings and sees each class they are waitlisted for, marked as waitlisted (not booked), with their current position.
Source: implied: a waitlist the member cannot look at is one they cannot rely on

### U-3: A waitlisted member is booked when a spot opens, and learns of it
Flow: A booked person cancels. The first eligible person on the waitlist is booked into the class without doing anything, and is told so. They then see the class as booked in their bookings.
Source: request (full classes do not turn people away); choice for the automatic booking

### U-4: A member leaves a waitlist
Flow: The member opens a class they are waitlisted for, chooses to leave, and is told they are no longer on it.
Source: implied: anything a person can join they can withdraw from

### U-5: A member tries to join a waitlist where joining cannot work
Flow: The member is signed out, already booked, already waitlisted, the class has room, they are not allowed to book that class, booking has closed, or the waitlist cannot take more people. They are refused, told why in each case, and nothing is added.
Source: implied: the unhappy paths of U-1

### U-6: A member who is not on the waitlist tries to book a class whose open spot is reserved for the waitlist
Flow: A spot has opened but people are waiting for it. The member tries to book directly. They are not given the spot and are offered the waitlist instead.
Source: implied: a waitlist is pointless if newcomers can take the spot first

### U-7: A waitlisted member who can no longer book is passed over when their turn comes
Flow: When their turn comes the member is no longer allowed to book that class (for example the membership lapsed, or the booking would overlap another class they are in). They are not booked, are told, and the next person gets the spot.
Source: implied: the person ahead may not be able to take the spot

### U-8: A waitlisted member whose class reaches the end of booking without a spot
Flow: Booking for the class closes while the member is still waiting. Their entry ends and they are told they did not get a spot.
Source: implied: every piece of state has an end

### U-9: A booked member's spot is freed in other ways than their own cancellation
Flow: Staff remove a booking, staff raise the class capacity, or a booked member's account is removed. The freed spot or spots go to the people at the front of the waitlist.
Source: implied: "a spot opens" has more causes than one cancel button

### U-10: A staff member sees and manages a class's waitlist
Flow: Staff open a class and see who is waitlisted, in order, with when each joined. They can remove an entry. They can also see how past entries ended.
Source: implied: the operator's work (observe, correct)

### U-11: Staff change or cancel a class that has a waitlist
Flow: Staff lower the capacity, cancel the class, or move it to another time. Booked and waitlisted members are looked after consistently.
Source: implied: existing class management meets the new waitlist

### U-12: Several members act at the same moment on the same class
Flow: Two bookings are cancelled at once, a member joins as a spot opens, a member leaves while their turn arrives, a member presses join twice. Each person ends in exactly one sensible state.
Source: implied: where the parts meet

### U-13: An instructor or staff member checks who is coming to a class
Flow: They open the class roster or attendance. They see only people who are booked, not people who are waiting.
Source: implied: a waitlisted person has no spot

### U-14: The operator switches the waitlist on or off, watches it, recovers it after trouble, deploys it onto live data and can go back
Flow: The operator turns the feature off and on, finds out what happened to a particular promotion, brings the system back after an outage with entries still waiting, releases the feature with classes and bookings that already exist, and returns to the previous version if needed.
Source: implied: start, stop, observe, recover, carry on with existing data, go back

## Clauses

### C-1: A full class offers the waitlist to members who could otherwise book it
Observable: A signed-in member who is not booked in a full class, and who would be allowed to book it if it had room, sees an action to join its waitlist instead of a dead-end refusal.
Source: request

### C-2: A class is full when booked people number at least its capacity
Observable: Capacity 10 with 10 booked and 3 waitlisted shows as full, with no spots left (not as -3). Capacity 10 with 9 booked and nobody waitlisted is not full.
Source: implied: "full classes"

### C-3: The waitlist belongs to one class session
Observable: When the Monday 18:00 session of a class that recurs weekly is full, joining its waitlist puts the member on that session's list only; the Wednesday session shows its own state and its own list.
Source: implied: fullness is a property of one session, so the list that fixes it is too

### C-4: Joining places the member at the end of the waitlist
Observable: With 3 people on the waitlist a member joins and is 4th; the 3 are still ahead of them in the same order.
Source: request

### C-5: After joining, the member is told their position
Observable: Joining as 4th shows position 4 (position 1 means next in line).
Source: implied: U-1

### C-6: Joining tells the member they will be booked automatically and that normal cancellation rules then apply
Observable: The join confirmation states that the member will be booked into the class without further action if a spot opens, and that the booking is subject to the app's usual cancellation rules from then on. The wording is not fixed.
Source: choice: the request does not say whether a spot is given automatically or offered; automatic booking is chosen (C-24) and a member must know that before they accept it

### C-7: Joining takes nothing from the member
Observable: After joining, the member has no booking in the class, no class credit or payment has been used for it, and any balance they hold is unchanged.
Source: choice: the request is silent on cost; charging at joining would charge people who may never get a spot

### C-8: A member who is already booked in the class cannot join its waitlist
Observable: The join is refused with a statement that they are already booked; no waitlist entry exists afterwards.
Source: implied: U-5

### C-9: A member already on the waitlist who joins again is not added twice
Observable: Pressing join twice, or sending the join twice, leaves exactly one entry at the original position, and the member is told they are already waitlisted and at which position.
Source: implied: U-5, U-12

### C-10: A member cannot join the waitlist of a class that has room and nobody waiting
Observable: Capacity 10, 9 booked, empty waitlist: the join is refused with a statement that a spot is available, the member is offered a normal booking, and no entry exists.
Source: implied: a waitlist is for full classes

### C-11: A member who is not allowed to book the class cannot join its waitlist
Observable: Where a direct booking would be refused for any reason other than the class being full (for example lapsed membership, no credit, an overlapping booking), joining is refused too, with that same reason given, and no entry exists.
Source: implied: U-5; otherwise the waitlist would collect people who can never be given the spot

### C-12: A class whose booking has closed accepts no waitlist joins
Observable: At any moment when a direct booking of the class would be refused because booking is closed (for example it has started or ended), a join is refused with that reason, and one second before booking closes a join is still accepted.
Source: implied: U-5

### C-13: A signed-out visitor cannot join a waitlist
Observable: The visitor is asked to sign in and no entry is created. After signing in they can join as any member can.
Source: implied: U-5; a waitlist entry belongs to a member

### C-14: A member can only put themselves on a waitlist
Observable: No action available to an ordinary member adds a different member to a waitlist or removes a different member from one.
Source: implied: privacy and ownership of an entry

### C-15: A waitlist can hold at least 100 members, and if it cannot take more the join is refused clearly
Observable: Joins are never refused for reasons of length while the list has fewer than 100 entries. If an implementation limits the list, the join beyond that limit is refused with a statement that the waitlist is full and no entry is created.
Source: choice: the request gives no limit; a member relies on being able to join, and 100 is far above ordinary demand for one class, while leaving a limit free for the builder

### C-16: One waitlist entry is for one spot for the member who joined
Observable: A member's entry results, at most, in that member being booked into one spot; no entry asks for several spots or for another person.
Source: choice: the request is silent on groups or guests; one spot per member is the simplest thing that serves the request

### C-17: Spots go to waitlisted members in the order they joined
Observable: Members A, B, C join in that order; the first spot to open goes to A, the next to B; C never gets a spot before B does. (Under the automatic booking chosen in C-24, "goes to" means is booked into.)
Source: implied: "waitlist" means a queue, and anything else is unfair to those who waited

### C-18: Two joins at the same moment give two different positions
Observable: Two members press join in the same instant on a list of 3: one is 4th and the other 5th, never both 4th, and each is told their own position.
Source: implied: U-12

### C-19: When a member leaves, those behind them move up by one and the order of the rest is unchanged
Observable: List A, B, C, D. B leaves: A is 1st, C is 2nd, D is 3rd.
Source: implied: U-4

### C-20: A member who leaves and joins again goes to the end of the list
Observable: A is 1st, A leaves and rejoins a list of 4 others: A is 5th.
Source: choice: the request is silent on keeping places; losing a place on leaving stops people holding a place they do not intend to use

### C-21: A member sees their waitlisted classes and positions in their own bookings, apart from their bookings
Observable: A class the member is waitlisted for appears marked as waitlisted with their position, and never appears as booked. A class they are booked for never shows a position.
Source: implied: U-2

### C-22: A position shown is current at the time of viewing
Observable: List A, B, C. A leaves. C then opens the page (or refreshes it) and sees position 2, not 3.
Source: implied: U-2

### C-23: A member never sees who else is on a waitlist
Observable: No page, message or notice a member receives names or identifies another waitlisted member or the member who just cancelled; only their own position is shown.
Source: implied: privacy

### C-24: When a spot opens in a class with a waitlist, the first eligible waitlisted member is booked into it automatically
Observable: Capacity 10, 10 booked, A then B waitlisted and both allowed to book. A booked member cancels; A is shown as booked, is no longer waitlisted, and B is now 1st. "Eligible" means the member would be allowed to book the class under the booking rules the app already has, if it had room.
Source: choice: the request does not say whether the spot is offered or given; automatic booking never leaves a spot empty while someone waits and needs no second step from a member who may not be looking

### C-25: A member cancelling their booking frees their spot for the waitlist
Observable: The cancelled member's booking no longer exists, and the waitlist is advanced as in the previous clause.
Source: choice: follows from the automatic booking chosen in C-24; the request itself only requires that the freed spot reaches the waitlist

### C-26: Staff removing a booking frees the spot for the waitlist
Observable: Staff remove a booked member from a full class with a waitlist; the first eligible waitlisted member is booked.
Source: choice: follows from the automatic booking chosen in C-24; implied by U-9

### C-27: Raising a class's capacity by k frees k spots for the waitlist
Observable: Capacity 10 raised to 12 with 10 booked and 5 waitlisted: the first 2 eligible waitlisted members are booked, the other 3 remain and are now 1st, 2nd and 3rd.
Source: choice: follows from the automatic booking chosen in C-24; implied by U-9

### C-28: A booked member's account being removed frees their spot for the waitlist
Observable: When a booked member's account is deleted or disabled such that their booking ends, the first eligible waitlisted member is booked into the freed spot.
Source: choice: follows from the automatic booking chosen in C-24; implied by U-9

### C-29: When several spots are free at once, the first that many eligible members are booked, each into one spot
Observable: Two bookings are cancelled at the same moment with 4 waitlisted: the 1st and 2nd are booked, the 3rd and 4th remain and move to 1st and 2nd. Nobody is booked twice and no spot is given to two people.
Source: choice: follows from the automatic booking chosen in C-24; implied by U-12

### C-30: A freed spot is given to the waitlist within 60 seconds
Observable: Within 60 seconds of a spot being freed in a class whose waitlist holds an eligible member, that member shows as booked.
Source: choice: the request gives no time; members rely on "soon", and a spot that sits unfilled for long defeats the purpose, while 60 seconds leaves room for the builder

### C-31: While anyone is waiting, a spot cannot be taken by someone who is not first in line
Observable: Capacity 10, 10 booked, A waitlisted. A booked member cancels. A different member who is not on the waitlist then tries to book directly, at any moment before A has been given the spot: they are refused, told that the class has a waitlist, and offered the waitlist. When no one is waitlisted the same attempt on a class with room simply books.
Source: implied: U-6

### C-32: A waitlisted member who tries to book the class directly is told they are waitlisted
Observable: The member is not booked through that path; they are shown that they are on the waitlist and at which position.
Source: implied: the member already holds a place, so a second booking path must not duplicate it

### C-33: A class never has more booked members than its capacity because of waitlist promotions
Observable: After any mix of cancellations, joins and promotions at the same time, the number booked into a class never exceeds its capacity. (Where capacity is lowered below the booked number, existing bookings stay; that case is stated separately.)
Source: implied: "full" means no more people can come in

### C-34: Lowering capacity below the booked number removes nobody and promotes nobody until the booked number is below capacity
Observable: Capacity 10 with 10 booked and 3 waitlisted lowered to 8: all 10 stay booked; the 3 stay waitlisted; the first cancellation brings booked to 9 and nobody is promoted; booked must fall below 8 before the first waitlisted member is booked.
Source: implied: U-11; a waitlist must not be a reason to unbook a person who holds a booking

### C-35: A promotion charges the member exactly what a direct booking of that class would charge, at the moment of promotion
Observable: If booking the class directly uses one class credit or takes a payment of some amount, a promoted member is charged one credit or that amount when booked, and not before. If a direct booking costs nothing, a promotion costs nothing.
Source: choice: the request is silent on what is taken and when; charging at promotion keeps waitlist and direct booking equal and never charges someone who gets no spot

### C-36: A promotion either completes in full or changes nothing
Observable: If the booking or the charge cannot be completed, the member is not booked, not charged, and keeps their place on the waitlist unless they are passed over (see below); never booked without the charge a direct booking would make, and never charged without a booking.
Source: choice: follows from the automatic booking chosen in C-24; implied by "data not lost, nothing done half-way"

### C-37: A member who is no longer eligible when their turn comes is passed over and removed from the waitlist
Observable: A waitlisted member whose membership has lapsed, or whose booking would overlap another class they already hold, is not booked when a spot opens; their entry ends; the next eligible member is booked instead.
Source: choice: the request is silent; passing over keeps the spot from going unused, and removal stops the same member being passed over at every later spot

### C-38: A member who is passed over is told they were not booked and why
Observable: Within 60 seconds of being passed over, the member receives a notice naming the class, saying they were not booked, and giving the reason in plain terms (such as "membership has lapsed" or "overlaps another booking"). Wording is not fixed.
Source: choice: follows from passing a member over; a member relying on a place must not lose it in silence

### C-39: When no waitlisted member is eligible, the freed spot is open to direct booking
Observable: Capacity 10, 9 booked after a cancellation, one waitlisted member who is passed over: the class now shows one spot and any eligible member can book it directly.
Source: choice: follows from passing members over (C-37); implied by "a spot nobody can use should not be held"

### C-40: A promoted member is told they are booked
Observable: Within 60 seconds of being booked, the member receives a notice by the same channel or channels the app uses to confirm a direct booking, naming the class, its date and time, and saying they are booked. Where the app confirms a direct booking in no channel outside the app, the member instead sees a notice in the app the next time they open it. Wording is not fixed.
Source: choice: follows from automatic booking; the member may not be in the app, and a booking nobody knows about is missed

### C-41: A promoted member sees the booking in their bookings and no longer sees the waitlist entry
Observable: The class appears as booked in their bookings, and is absent from their waitlisted classes.
Source: choice: follows from the automatic booking chosen in C-24; implied by U-3

### C-42: A notice that cannot be delivered does not undo the booking
Observable: With the sending service unavailable, a promoted member is still booked, still sees the booking in their bookings, and the spot is still theirs.
Source: choice: follows from the automatic booking chosen in C-24; implied by "a delivery failure is not a reason to give the spot away"

### C-43: An undelivered notice is retried until it is delivered or the class starts
Observable: A notice that fails to send is sent again later without anyone acting; once delivered it is not sent again; after the class has started no more attempts are made.
Source: choice: the request is silent; members rely on being told, and a notice after the class has started helps nobody

### C-44: A promoted booking follows the app's normal cancellation rules from the moment it is made
Observable: A promoted member who cancels is treated exactly as a member who booked directly at that moment would be (same cutoff, same fee or credit return, if the app has any).
Source: choice: the request is silent; equal treatment is the loosest rule, and C-6 tells the member in advance

### C-45: A retried or repeated promotion of the same entry gives one booking, one charge and one notice
Observable: If the same promotion is processed twice, the member has one booking in the class, was charged once (if a direct booking charges at all), and received one promotion notice (a re-send after a failed delivery is not a second notice).
Source: choice: follows from the automatic booking chosen in C-24; implied by "a thing done twice that should happen once"

### C-46: A member is never both booked and waitlisted for the same class
Observable: At no time does a member's own bookings view, or staff's view, show the same person as booked and on the waitlist for one class.
Source: implied: never

### C-47: Promotions happen only while direct booking would be allowed
Observable: A cancellation made at a time when booking the class directly would be refused because booking is closed (for example the class has started) does not book anyone from the waitlist.
Source: implied: the waitlist cannot give what booking itself cannot

### C-48: When booking for a class closes, every remaining waitlist entry ends within 60 seconds
Observable: Within 60 seconds after booking closes the class's waitlist is empty, and no member's waitlisted classes show that class.
Source: choice: the request gives no time for U-8 (state with an end); 60 seconds is the loosest figure a member can rely on

### C-49: A member whose entry ended at the close of booking is told they did not get a spot
Observable: Within 60 seconds after booking closes, each such member receives a notice naming the class and saying they were not booked. Wording is not fixed.
Source: choice: the request is silent; a member waiting for a spot who gets neither spot nor word will plan wrongly

### C-50: Every waitlist entry ends in a recorded outcome
Observable: For any entry, staff can find one of: booked, left by member, removed by staff, passed over (with reason), class cancelled, account ended, or closed without a spot.
Source: implied: a piece of state with no end; supports U-10

### C-51: A member can leave a waitlist at any time before they are booked or it closes
Observable: After leaving, the member is told they are off the list, they are not on the staff view of the list, nothing is charged, and no penalty applies.
Source: implied: U-4

### C-52: Leaving a waitlist the member is not on changes nothing and says so
Observable: Leaving twice, or leaving after the entry has ended, tells the member they are not on the waitlist and changes nobody else's position.
Source: implied: U-12

### C-53: A member who asks to leave just after being booked is told they are booked, and the booking stands
Observable: Member A's turn arrives and A is booked; A's leave request, which arrives after, is answered with a statement that A is booked in the class (not that A left the list); A's booking is unchanged and can be cancelled the normal way.
Source: choice: the request is silent; cancelling a booking on a "leave" request would surprise members

### C-54: A member who leaves just before their turn is not booked, and the next member is
Observable: Member A's leave is accepted first; then a spot opens: A is not booked, B is.
Source: choice: follows from the automatic booking chosen in C-24; implied by U-12

### C-55: Cancelling a booked member's booking works exactly as it did before the waitlist
Observable: The same cutoff, fee, credit return and confirmation apply to the cancelling member as before; only what happens to the freed spot is new.
Source: implied: what must not change

### C-56: Booking a class that is not full and has nobody waiting works exactly as it did before
Observable: Capacity 10, 9 booked, empty waitlist: a member books directly and is charged as before; the same steps and same results as before the waitlist.
Source: implied: what must not change

### C-57: A full class still shows as full wherever the app lists or filters classes by availability
Observable: A full class with a waitlist does not appear among "has spots" results and shows no available spots; its waitlist action is additional to that.
Source: implied: what must not change

### C-58: Waitlisted members are not counted as booked anywhere
Observable: Booked count, spots taken, spots left, revenue and attendance figures for a class are the same with or without people waiting.
Source: implied: a waitlisted person has no spot

### C-59: A roster or attendance list shows only booked members
Observable: A class with 10 booked and 3 waitlisted shows 10 names on the roster, none of the 3.
Source: implied: U-13

### C-60: Staff can see a class's waitlist in order, with when each member joined
Observable: Staff see each waitlisted member's name in order with the time they joined; the order matches the order in which spots will be offered.
Source: implied: U-10

### C-61: Only staff can see who is on a waitlist or remove an entry
Observable: A request by an ordinary member to see the list of names or remove another member's entry is refused and shows or changes nothing.
Source: implied: privacy; U-10

### C-62: Staff can remove a member from a waitlist
Observable: After removal the member is not on the list and those behind them move up by one.
Source: implied: U-10

### C-63: A member removed by staff is told
Observable: The member receives a notice naming the class and saying they were removed from its waitlist. Wording is not fixed.
Source: choice: the request is silent; a person otherwise keeps waiting for a spot they will not get

### C-64: Staff can see how past entries ended
Observable: For a session that ended up to 90 days ago, staff see each entry's outcome (one of those listed in the clause on recorded outcomes) and when it ended.
Source: choice: the request is silent; staff must be able to answer "why wasn't I booked?", the information has to exist for that, and 90 days is chosen as how long such questions are asked

### C-65: A member's account being ended removes their waitlist entries without booking them
Observable: When a waitlisted member's account is deleted or disabled, they are on no waitlist and are not booked into any class from that moment on; those behind them move up.
Source: implied: a promotion must not go to an account that cannot use it

### C-66: Cancelling a class ends its waitlist
Observable: When staff cancel a class with a waitlist, every waitlisted member receives a notice naming the class and saying it was cancelled; nobody on its waitlist is booked or charged; the waitlist is empty.
Source: implied: U-11

### C-67: Moving a class to another time keeps its waitlist and its order and tells waitlisted members
Observable: Waitlist A, B, C for Monday 18:00 moves to Tuesday 19:00: all three remain in the same order; each gets the same kind of change notice that booked members of that class get, naming the new time. Members who can no longer take the new time are passed over at promotion if that makes them ineligible.
Source: choice: the request is silent; keeping places is the loosest rule that does not discard waiting members

### C-68: Joining and a spot opening at the same moment never strands a member
Observable: In any run of concurrent joins, cancellations and promotions, once everything has settled no class is left with an open spot and a waitlist containing an eligible member for longer than 60 seconds while the system is running.
Source: choice: follows from the automatic booking chosen in C-24 and the 60 seconds of C-30; implied by U-12

### C-69: Two spots freed at once go to two different members, in order
Observable: Two members cancel at the same instant, A, B, C waitlisted: A and B are booked, C is next in line and shows position 1; no member is skipped and none is booked twice.
Source: choice: follows from the automatic booking chosen in C-24; implied by U-12

### C-70: A member is never told they joined when they did not, nor told they failed when they joined
Observable: When a join cannot be completed (for example the system errors), the member is told it did not complete and no entry exists. A retry produces at most one entry. When it did complete the confirmation is shown.
Source: implied: U-12; a retry after an unclear failure must be safe

### C-71: The waitlist can be switched off, which stops new joins
Observable: With the waitlist switched off, a full class behaves as it did before (the member is refused because the class is full and no waitlist action is offered, and a join request is refused); switched on, the behaviour of C-1 applies.
Source: choice: the request is silent; start/stop is the operator's work and a switch is the simplest means that does not require removing the feature

### C-72: Switching the waitlist off does not disturb entries that already exist
Observable: With the waitlist switched off, members already waitlisted keep their position, are still booked when spots open, are told as in C-40, can still leave, and are still ended at the close of booking.
Source: choice: abandoning waiting members would be the worst outcome of a switch used in a hurry

### C-73: Staff can find out what happened to any promotion, passing over or failed notice
Observable: For a given class and member the operator can find when a promotion, a passing over, or a notice failure happened, which class and which member it concerned.
Source: choice: the request is silent on observing; the operator must be able to answer a member who says they were never told or never booked

### C-74: After an outage, promotions and closures that were due are carried out within 5 minutes of the system being available
Observable: The system is unavailable while a booked member cancels, and while booking for another class closes. Within 5 minutes after it is available again, the first eligible waitlisted member is booked into the freed spot, and the other class's remaining entries have ended with notices sent.
Source: choice: U-14 (recover) requires catching up but the request gives no time; 5 minutes is chosen, and the promotion part follows from the automatic booking of C-24

### C-75: Releasing the waitlist leaves every existing class, booking and count as it was
Observable: Immediately after release, each class shows the same booked members and the same number of spots as just before; every class has an empty waitlist; every existing full class offers the waitlist.
Source: implied: U-14 (carry on with data that already exists)

### C-76: A booking made while the release is being deployed is not lost or duplicated
Observable: A member books a class while the new version is being rolled out; afterwards they have exactly one booking in it and the class's counts include them.
Source: implied: U-14

### C-77: Returning to the version before the waitlist keeps every booking, including those made by promotion
Observable: After returning, every member who was booked before the return, including those booked from a waitlist, is still booked exactly once; no booking is lost, duplicated or charged again.
Source: implied: U-14 (go back to the version before)

### C-78: After returning to the version before and releasing the waitlist again, members who were waiting are still waiting in the same order
Observable: List A, B, C is present at the time of the return; after the waitlist is released again, A, B, C are still waitlisted in that order, and any spot that opened in between is given to A within 5 minutes.
Source: choice: the request is silent; keeping the waiting members is the loosest rule that does not discard them for a version change

### C-79: Cancelling a booking, changing capacity or cancelling a class succeeds for the person doing it even when the waitlist work cannot be completed
Observable: With the notification service unavailable, or with 500 members waitlisted, staff cancelling a class or a member cancelling a booking sees success; the freed-spot and notice work is completed within the times stated elsewhere (or, for what cannot be sent, retried).
Source: implied: the runtime may time out or limit synchronous work, so the actor's action cannot depend on it

### C-80: Notices to a large waitlist are all delivered, though they may be spread out
Observable: Cancelling a class with 500 waitlisted members results in all 500 receiving the notice within 1 hour. The figure is unconfirmed: it depends on the sending limits of the delivery service in use, which this request does not name.
Source: choice: unconfirmed sending quota; the loosest bound that still lets a member rely on being told the same day

### C-81: Class times and booking cutoffs are those of the class's own location and local time
Observable: A notice names the class time in the local time of the class's location with its zone; booking closes at the same local wall-clock moment before and after a daylight-saving change, as it does today.
Source: implied: the app already has times; a notice that uses a different zone would send members to the wrong hour

### C-82: Nothing in a non-production environment is sent to real members
Observable: In development and test environments no notice is delivered to a real member's address or number; they are captured where a developer can read them or delivered to test addresses only.
Source: implied: what must never happen; a test run telling real members they were booked

### C-83: Promotion notices sent from production are accepted by recipients' mail systems
Observable: Where the channel is email, a promotion notice to an address at a large mailbox provider arrives in the inbox, not rejected and not in a spam folder, because the sending domain is authenticated (SPF, DKIM and DMARC aligned). If the app's confirmation channel is not email, the equivalent requirement of that channel (such as app-store push permission) holds instead. Whether email is the channel is unconfirmed.
Source: choice: the request does not name the channel; the delivery requirement for production is stated as the behaviour it forces

### C-84: A class with an open spot but a non-empty waitlist still offers the waitlist and takes joins at the end
Observable: Capacity 10, 9 booked, 2 waitlisted whose spot is not yet filled: a further member who is allowed to book sees the waitlist action, joins, and is 3rd; a direct booking by them is refused.
Source: implied: U-6; the spot belongs to those already waiting

### C-85: A member may be on any number of waitlists at once, including for classes that overlap in time
Observable: A member waitlisted for Monday 18:00 class X can also join the waitlist for Monday 18:00 class Y; a join is not refused because of another waitlist entry (only because of another booking they hold).
Source: choice: the request is silent; a waitlist entry is not a booking, so refusing would stop members hedging between full classes
