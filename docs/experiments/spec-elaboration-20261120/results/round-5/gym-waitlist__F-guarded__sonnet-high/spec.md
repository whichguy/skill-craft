## Use cases

### U-1: A signed-in member joins the waitlist of a full class, to keep a chance at a place
Flow: The member opens a class whose booked count equals its capacity. Where booking used to end in a "full" refusal, they are offered a way to join the waitlist. They use it and are shown that they are on the waitlist, for which class, and at which position. Joining costs them nothing.
Source: request

### U-2: A member tries to join a waitlist and is refused
Flow: The member tries to join and cannot: they are not signed in, they already hold a place in that class, they are already waiting for it, the waitlist already holds 20 people, the booking cutoff has passed, the class is cancelled, or they fail a condition that would also stop them booking. They see which of these it is and nothing is added to the waitlist.
Source: implied: U-1 has an unhappy path for every condition that decides whether joining is allowed

### U-3: A waiting member gets a place without doing anything
Flow: A place in the class becomes free. The member who has waited longest and is eligible is booked into the class, is charged exactly what a direct booking would have cost, and is told by message. The class shows the member as booked.
Source: request: "so full classes don't turn people away"

### U-4: A waiting member who cannot take the place is passed over
Flow: A place becomes free and the member at the front of the waitlist no longer meets a booking condition. They are taken off the waitlist and told why. The next waiting member is considered in their place.
Source: implied: U-3, a place cannot be given to someone who could not have booked it

### U-5: A member checks where they stand
Flow: The member opens their own classes and sees each class they are waiting for, its start time, and their position, apart from the classes they are booked into.
Source: implied: U-1, joining a queue is pointless if the member cannot see where they are in it

### U-6: A member leaves a waitlist
Flow: The member opens a class they are waiting for and leaves the waitlist. They no longer wait, are not charged anything, and the members behind them move up by one.
Source: implied: anyone who can join a queue must be able to leave it

### U-7: A waitlist ends around a member
Flow: The class is cancelled or deleted, is rescheduled, passes the point where bookings close, or the member's account is removed or deactivated. The member's waitlist entry ends or carries on as stated below and the member is told where the app tells booked members the same thing.
Source: implied: a waitlist entry belongs to a class and a member, and either can change or go

### U-8: Two things happen at once on the same class
Flow: Several members join at the same moment, or two bookings are cancelled at the same moment, or a member joins just as a place frees, or a member cancels and tries to book again straight away. Every member ends up in exactly one coherent state and no place is given twice.
Source: implied: a busy class is exactly where simultaneous actions occur

### U-9: Staff see who is waiting for a class
Flow: A staff member opens a class and sees its waitlist in order, apart from the people booked into it.
Source: implied: staff run the classes and need to know demand

### U-10: Staff change a class that has a waitlist
Flow: Staff raise or lower its capacity, cancel a member's booking, cancel the class, or change its time. The waitlist responds as stated below.
Source: implied: classes are managed by staff today and the waitlist hangs off every way a class changes

### U-11: Members book and cancel as they did before
Flow: A member books a class that has a free place, books it again by mistake, or cancels a booking. It works as it did before the waitlist existed.
Source: implied: the request adds to booking, it does not replace it

### U-12: The waitlist is introduced to an app that has live data, and may be withdrawn
Flow: The waitlist is switched on while classes, bookings and members already exist. Later, it may be switched off again.
Source: implied: the app is already running

### U-13: Something fails while a place is being given away
Flow: The system fails part way through giving a freed place to the first waiting member, or the message to them cannot be sent.
Source: implied: a thing it depends on failing

## Clauses

### C-1: A full class offers the waitlist
Observable: A signed-in member viewing a class whose booked count equals its capacity sees an action to join its waitlist, where booking used to be refused with a "full" message. A class whose capacity is not reached does not show the action.
Source: request

### C-2: Joining adds the member at the back
Observable: A member who joins a class with 3 people waiting is shown position 4. A member who joins a class with nobody waiting is shown position 1.
Source: implied: U-1, a queue adds at its end

### C-3: Joining confirms where the member stands
Observable: On success the member sees the class name, its start date and time, and their position.
Source: implied: U-1

### C-4: Joining costs nothing
Observable: Joining leaves the member's class credits, pass balance, payments and booking counts exactly as they were before.
Source: implied: U-1, nothing is yet received

### C-5: Waiting members do not occupy a place
Observable: A class's booked count, remaining places and attendee roster list only booked members. A waiting member is in none of them, and 4 people waiting on a class of 10 booked of 10 still shows 10 booked of 10.
Source: implied: U-1, a waiting member holds no place

### C-6: Joining is refused when the member is not signed in
Observable: A visitor who is not signed in who tries to join is handled as booking handles a visitor who is not signed in, and no waitlist entry exists afterwards.
Source: implied: U-2

### C-7: Joining is refused when the member already holds a place
Observable: A member booked into the class who tries to join sees that they are already booked; the waitlist is unchanged.
Source: implied: U-2

### C-8: Joining twice leaves one entry
Observable: A member already waiting who joins again, or whose join request is sent twice, still has one entry and the same position as before, and is shown that position and that they were already waiting.
Source: implied: U-2, a repeated or retried request must not queue someone twice

### C-9: A waitlist holds at most 20 people
Observable: When 20 members are waiting for a class, the 21st member who tries to join is refused with a message that the waitlist is full, and the 20 entries and their order are unchanged. Only entries still waiting count toward the 20: once one leaves, is booked, is passed over or ends, the next member can join. The figure 20 is chosen here and is unconfirmed by the requester.
Source: choice: an unbounded queue is not a useful promise to a member, 20 is more than a fully booked class is likely to refill from

### C-10: A member may wait for any number of classes
Observable: A member already waiting for 1, 5 or 12 other classes is not refused joining one more for that reason.
Source: choice: the request sets no such limit

### C-11: Joining is refused once bookings have closed
Observable: A member who tries to join after the booking cutoff of the class is refused with a message that bookings have closed. The booking cutoff is the moment after which the app stops accepting new bookings for that class today, or, where the app has none, the class's start time.
Source: implied: U-2, a place cannot be gained in a class that cannot be booked

### C-12: Joining a cancelled or deleted class is refused
Observable: A member who tries to join the waitlist of a cancelled or deleted class is refused with a message that the class is not running, and nothing is added.
Source: implied: U-2

### C-13: Joining is refused when the member would fail a booking condition
Observable: A member who would be refused a booking of a class with a free place is refused joining the waitlist of that class, and sees the same reason. The conditions are those that exist today, whichever of these the app has: membership not active, no class credit or pass balance left, a booking limit per day, week or month reached, an overlapping booking at the same time, the member suspended or blocked. This specification adds none and removes none.
Source: implied: U-2, a member who could never take a place is not queued for one

### C-14: A member can only join for themselves
Observable: A request to join made as one member naming another member is refused, and the other member's waitlist standing is unchanged.
Source: implied: U-1, a member is only able to act on their own bookings

### C-15: Joining a class that has a free place books the member instead
Observable: A member who joins a class that, at that moment, has a free place and nobody waiting is booked into the class as in a direct booking, and is told they are booked and not waiting.
Source: choice: the member's evident aim is a place; this covers a place freeing between viewing and joining

### C-16: A freed place goes to the member who has waited longest
Observable: When a place in the class becomes free and the waitlist is not empty, the active entry that joined earliest and is eligible becomes booked into the class, so that the member with position 1 becomes booked before the member with position 2.
Source: request: "so full classes don't turn people away"; choice: first come, first served

### C-17: The ways a place becomes free
Observable: A place counts as freed, and C-16 applies, when: a member cancels their booking; staff cancel or remove a member's booking; the member's account is removed or deactivated so that their booking ends; a booking is removed by any other existing rule of the app (for example an automatic cancellation); or capacity is raised so that booked count is below capacity.
Source: implied: U-3, a place can open by any of those routes and the waitlist must serve all of them, a cancel is not the only one

### C-18: Raising capacity gives places to as many waiting members as the raise opens
Observable: Raising capacity from 10 to 13 with 10 booked and 5 waiting books the members at positions 1, 2 and 3, leaving the members at 4 and 5 waiting as the new positions 1 and 2.
Source: implied: U-10

### C-19: The waiting member does nothing to get the place
Observable: The member does not have to be signed in, open the app, or confirm anything for the place to be given; they are booked.
Source: choice: no claim step, it keeps the promise of the request that full classes do not turn people away with the least that a member must do

### C-20: The place is given within 60 seconds
Observable: Within 60 seconds of a place becoming free while an eligible member is waiting, that member is booked. The figure 60 seconds is chosen here and is unconfirmed.
Source: choice: bound where the request gives none, an unbounded delay would let a place sit empty while members wait

### C-21: Members are charged what a direct booking costs, at the time they are given the place
Observable: A promoted member's class credit, pass balance or payment changes by exactly what a direct booking of that class would have changed it, once, at the time they are booked. If a booking costs nothing today, nothing is charged.
Source: implied: U-3; C-4 means nothing was charged when they joined

### C-22: A promoted booking is an ordinary booking
Observable: The member sees the class in their booked classes, it counts as a booked place, and cancelling it follows the same cancellation rules, penalties and refunds that apply to any booking of that class at that time.
Source: implied: U-3

### C-23: A member who no longer meets a booking condition is passed over
Observable: At the time a place is to be given, an entry whose member now fails any condition listed in C-13 is not booked; their entry is removed, and the place goes to the next earliest eligible entry.
Source: implied: U-4, the same conditions C-13 names apply again at the time of giving, as the member's situation may have changed since they joined

### C-24: A member who is passed over is told
Observable: The member receives a message naming the class and its start time, saying that they were not given a place and which condition from C-13 stopped it.
Source: implied: U-4, otherwise they would wait for a place that is not coming

### C-25: A member who is passed over keeps no priority
Observable: A member who was passed over and then joins the same waitlist again is at the back, with position equal to the number waiting plus 1.
Source: choice: priority would reward a member who was the reason for the delay

### C-26: A freed place with nobody eligible waiting becomes bookable by anyone
Observable: When a place is freed and the waitlist is empty, or every waiting entry has been passed over under C-23, the class shows a free place and any eligible member can book it directly.
Source: implied: U-4, a place must not stay empty because a waitlist exists

### C-27: A freed place is not available to anyone else while an eligible member is waiting
Observable: From the moment a place is freed while an eligible member is waiting, a direct booking attempt of that class by any other member, including the member who just cancelled, does not succeed: they are told the class is full and offered the waitlist. This holds whether or not the place has yet been given (C-20), and the place is given to the waiting member and not lost to the attempt.
Source: implied: U-8, an order of waiting is meaningless if a newcomer can take the place first

### C-28: Each freed place goes to exactly one member
Observable: When 2 bookings in a class of 10 are cancelled at the same moment with 5 waiting, exactly the members at positions 1 and 2 are booked, each once, the booked count is 10, and the members at positions 3, 4 and 5 become positions 1, 2 and 3.
Source: implied: U-8

### C-29: A class never holds more booked members than its capacity because of the waitlist
Observable: However many places are freed or members join at once, the booked count of a class after any waitlist action never exceeds its capacity.
Source: implied: U-8; also existing rule that capacity is a limit

### C-30: Simultaneous joins get different positions
Observable: When 3 members join a waitlist that holds 2 at the same moment, afterwards their positions are 3, 4 and 5 once each, in the order the system accepted their requests; no two share a position and there is no gap.
Source: implied: U-8

### C-31: A member holding a place cannot also be waiting
Observable: If a member who is waiting for a class becomes booked into it by any route (including staff booking them, where staff can do so today), their waitlist entry is removed and they are not booked a second time.
Source: implied: U-8, one member never holds two places in one class

### C-32: The promoted member is told once
Observable: The member receives exactly one message that they have been given a place, naming the class and its start date and time and saying they are booked. No second message is sent for the same place.
Source: implied: U-3, the member has to learn that they hold a place or the place is wasted

### C-33: Waitlist messages go by the channel booking confirmations use
Observable: The messages of C-32 and C-24 arrive by the channel or channels by which the app confirms a booking to the member today. Where the app sends no booking confirmations today, it arrives by email at the address on the member's account.
Source: choice: no channel is named by the request, the confirmation channel is the one the member already watches

### C-34: A failed message does not undo the booking
Observable: When the message in C-32 or C-24 cannot be sent, the member is booked, or passed over, all the same, and the booked class shows in their classes.
Source: implied: U-13

### C-35: A failure while giving the place loses neither the place nor the queue
Observable: If giving a place fails part way, afterwards the member is either booked and no longer waiting, or still waiting at the same position and the place free to be given within the time in C-20; no member is both booked and waiting, no place is lost and no member is booked twice.
Source: implied: U-13

### C-36: A failure while giving the place does not undo the cancellation that freed it
Observable: A member whose cancellation freed a place sees their cancellation succeed even when giving the place to the waiting member fails.
Source: implied: U-13, the canceller did nothing wrong

### C-37: The waiting member sees their position
Observable: In the member's own classes, each class they are waiting for appears with its name, start time, and position (1 is next), marked as waiting and not as booked, with an action to leave. A member waiting for no class sees no waiting entries.
Source: implied: U-5

### C-38: Position moves up as others leave the queue
Observable: A member at position 4 is shown position 3 once one member ahead of them is booked, leaves, is passed over, or has their entry end.
Source: implied: U-5

### C-39: Members cannot see who else is waiting
Observable: A member sees only their own position, never another member's name or details on a waitlist; the booked roster is shown to members as it is today.
Source: implied: other members' details are not for members to see

### C-40: A member can leave a waitlist at any time while waiting
Observable: After a member leaves, they no longer appear on the waitlist, are shown that they left, and are not booked when a place frees.
Source: implied: U-6

### C-41: Leaving moves those behind up by one
Observable: With members at positions 1 to 5, when the member at position 2 leaves, the members who were 3, 4 and 5 become 2, 3 and 4 and the member at 1 is unchanged.
Source: implied: U-6

### C-42: Leaving costs nothing and carries no penalty
Observable: Leaving a waitlist leaves the member's credits, pass balance and payments unchanged and adds no late-cancellation penalty, however close to the class start.
Source: implied: U-6; C-4

### C-43: Leaving when not waiting changes nothing
Observable: A request to leave from a member who is not waiting (for example repeated or retried) tells them they are not on the waitlist and changes no one's position.
Source: implied: U-6

### C-44: A member can only leave for themselves
Observable: A request to leave made as one member naming another member's entry is refused and that entry stays.
Source: implied: U-6

### C-45: Waiting ends at the booking cutoff
Observable: At the booking cutoff of the class (as in C-11), every remaining entry ends. Nobody is booked from the waitlist at or after that moment, and the class's waitlist, once the cutoff has passed, lists no one waiting.
Source: choice: a place found after bookings close cannot be used, and a queue past that point has no meaning

### C-46: Entries past the cutoff count as ended however they are read
Observable: A member who opens their classes after the cutoff sees the class as not waiting, even when no routine clean-up has yet run, and a place freed after the cutoff is not given to anyone from the waitlist.
Source: implied: C-45; the runtime may not run a clean-up at the exact moment

### C-47: Cancelling or deleting a class ends its waitlist
Observable: When a class is cancelled or deleted, every waiting entry ends, no one is booked from it, no charge is made, and each waiting member is told that the class is cancelled in the way booked members are told.
Source: implied: U-7

### C-48: Rescheduling a class keeps its waitlist
Observable: When a class's date or time is changed, its waiting members stay waiting at the same positions, are told of the change in the way booked members are told, and the booking cutoff of C-11 is that of the new time; if the new time's cutoff has already passed, the entries end as in C-45.
Source: choice: the members waited for this class, they can leave if the new time does not suit them

### C-49: Removing or deactivating a member removes their waiting entries
Observable: When a member's account is removed or deactivated, they appear on no waitlist and the members behind them move up by one on each.
Source: implied: U-7

### C-50: Lowering capacity does not remove anyone and gives no places
Observable: Lowering the capacity of a class below its booked count removes no booked member, books no waiting member, and keeps the waitlist as it was. A place is next given when the booked count falls below the new capacity.
Source: implied: U-10

### C-51: Staff see the waitlist in order
Observable: A staff member opening a class sees the waitlist as a list in order, with for each entry the member's name, their position and the date and time they joined, and sees an empty-waitlist state when no one is waiting.
Source: implied: U-9

### C-52: Only staff see the waitlist's members
Observable: A signed-in member who is not staff cannot open the staff view of a waitlist, and a visitor who is not signed in cannot either; both are refused.
Source: implied: U-9; C-39

### C-53: The roster staff use lists booked members only
Observable: The attendee roster of a class shows booked members only; waiting members are shown in the separate waitlist view.
Source: implied: U-9; C-5

### C-54: Rules hold on every path
Observable: The waitlist limit of C-9, the cutoff of C-11, the conditions of C-13 and the member-only checks of C-14 and C-44 give the same result whether the action is made from the app's screens, from any other client, or by a direct call to the app's interface.
Source: implied: a rule held in one path and not another can be bypassed

### C-55: Booking a class with a free place is unchanged
Observable: A member who books a class with a free place is booked as before, with the same checks, cost and confirmation.
Source: implied: U-11; existing rule

### C-56: Booking a class that is full still cannot be done directly
Observable: A direct booking of a full class does not put the member into the class; the member is told it is full and offered the waitlist.
Source: implied: U-1; existing rule that a full class has no place to book

### C-57: A member cannot book the same class twice
Observable: A member already booked into a class who books it again is not booked a second time and sees the same refusal as before the waitlist.
Source: implied: U-11; existing rule

### C-58: Cancelling a booking is unchanged for the canceller
Observable: Cancelling a booking applies the same cancellation window, penalty and refund as before, and shows the same confirmation to the canceller; the waitlist changes nothing about what they pay or are refunded.
Source: implied: U-11; existing rule

### C-59: Class details, capacity and times are shown as before
Observable: Every screen of a class that existed before shows the same name, time, capacity and booked count as before, with the waitlist's additions only.
Source: implied: U-11; what must not change

### C-60: Existing data is untouched when the waitlist starts
Observable: At the time the waitlist is switched on, every existing class, booking, member and balance is unchanged, no member is booked or charged, and classes full at that time show the waitlist offer with an empty waitlist.
Source: implied: U-12

### C-61: Withdrawing the waitlist loses no booking
Observable: When the waitlist is switched off, every member booked at that time, including those booked from a waitlist, is still booked, no one waiting is booked or charged, and a full class is refused as it was before the waitlist.
Source: implied: U-12, going back to the version before

### C-62: Waiting members receive no messages beyond those listed
Observable: The only messages to a waiting member from the waitlist are: being given a place (C-32), being passed over (C-24), the class being cancelled or deleted (C-47), and the class being rescheduled (C-48). A change of position sends none.
Source: choice: no message feature beyond what the request needs

### C-63: Waitlist actions are answered within 5 seconds
Observable: A join or leave request is answered with its result within 5 seconds, under the load of a class whose 20-person waitlist is changing at once. The figure 5 seconds is chosen here and is unconfirmed.
Source: choice: the runtime of the app, undetermined here, will have a request timeout and members must not be left with a spinner

### C-64: Giving a place does not hold up the canceller
Observable: With the channel that carries the promoted member's message delayed by 30 seconds, the canceller still sees their cancellation confirmed within the 5 seconds of C-63.
Source: implied: runtime limit, sending messages is slow and failure-prone and must not slow a cancel (C-58)

### C-65: Times are judged on one clock
Observable: The booking cutoff, joining time and order of joining are decided by the server's clock, not by a member's device, so that a member whose device clock is wrong has the same result as any other.
Source: implied: runtime; choice: the server's clock because it is the only one every member shares

### C-66: The class screen of a waiting member shows their standing
Observable: A member who is waiting for a class and opens it sees their position and an action to leave, and does not see the action to join.
Source: implied: U-5, U-6; C-8
