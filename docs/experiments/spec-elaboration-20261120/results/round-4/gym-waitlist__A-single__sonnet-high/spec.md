## Use cases

### U-1: A member who wants a full class is offered the waitlist instead of being turned away
Flow: The member tries to book a class that has no free places. They are told the class is full, they are not booked, and they are offered the choice to join that class's waitlist. The class shown in any class listing as full carries the same offer.
Source: request

### U-2: A member joins a class's waitlist and sees where they stand
Flow: The member chooses to join the waitlist of a full class. They are told they are on the waitlist and are shown their position (1 = next in line). They are not booked.
Source: request

### U-3: A waiting member gets a place automatically when one frees up
Flow: A booked member cancels. Without anyone doing anything, the member who has waited longest for that class is booked into the freed place, and finds out about it.
Source: request ("so full classes don't turn people away" is only met if a waiting member ends up in the class)

### U-4: A member checks their waitlist standing
Flow: The member looks at their own classes. Classes they are booked into and classes they are only waiting for are shown as different things; for each waiting class they see their current position. As people ahead of them leave or get a place, the position goes down.
Source: implied: U-2 (a position that is shown must stay true)

### U-5: A member leaves a waitlist
Flow: A waiting member withdraws from the waitlist. They are told they are no longer on it, and everyone behind them moves up one place.
Source: implied: U-2 (a person who can join can change their mind)

### U-6: The first and the last place in line
Flow: (a) A member joins a full class whose waitlist is empty and is told position 1. (b) A member joins a class that already has 499 members waiting and is told position 500. (c) A booked member cancels a full class that has nobody waiting; the place simply becomes free and the next member to book it gets it, as today.
Source: implied: the empty case and the largest case of U-2 and U-3

### U-7: A member repeats an action or asks for something that makes no sense
Flow: The member (a) joins a waitlist they are already on, (b) tries to join the waitlist of a class they are already booked into, (c) tries to join the waitlist of a class that has free places, (d) tries to join the waitlist of a class that has started, ended, been cancelled or does not exist, or (e) tries to leave a waitlist they are not on. Each is refused with a reason; nothing changes for them or anyone else.
Source: implied: unhappy paths of U-2 and U-5

### U-8: A member who may not book the class tries to wait for it, or stops being able to by the time a place frees up
Flow: (a) A member who would be refused a booking for any reason other than the class being full tries to join its waitlist and is refused with a reason. (b) A member who legitimately joined the waitlist is, when their turn comes, no longer allowed to book the class; they are not booked and the place goes to the next member in line.
Source: implied: the request cannot mean the waitlist lets people into classes the booking rules would refuse them

### U-9: Several people act at the same moment
Flow: Two members join the same waitlist at the same time; two places free up at the same time; a booked member cancels at the same instant as a new member tries to book directly. Every member sees a consistent result: no class is over capacity, no place goes to two members, and no direct booker takes a place ahead of someone already waiting.
Source: implied: a booking app with many members acting at once

### U-10: Staff change what a class holds
Flow: Staff (a) raise a full class's capacity by some number of places, (b) remove a booked member from a class, (c) cancel a class that has people waiting, or (d) look at a class's roster. For (a) and (b) the freed places go to the waiting members in order. For (c) the waiting members are no longer waiting for anything. For (d) staff can see who is waiting and in what order.
Source: implied: places free up in ways other than a member cancelling; the staff who run the class need to know who is waiting

### U-11: The class starts while members are still waiting
Flow: The time arrives at which the class can no longer be booked. Members still on its waitlist are not booked and no longer appear as waiting; a place that frees up after that point is not given to anyone from the waitlist.
Source: implied: a waitlist for a class that has begun serves nobody

### U-12: The operator brings the feature in, restarts, and can go back
Flow: The operator deploys the new version onto the data that exists today and starts the app with the settings used today. Existing classes and bookings are as they were, every waitlist is empty. They restart the app at any time and no waiting member loses their place. They can return to the previous version and every booking, including ones created by waitlist promotion, is intact there.
Source: implied: start, restart, carrying on with existing data, going back

### U-13: Everyone who books and cancels as they do today
Flow: A member books a class that has free places, or cancels a booking, exactly as before, in a class with or without a waitlist feature in play.
Source: implied: where this touches things that already exist

## Clauses

### C-1: Booking a full class never produces a booking
Observable: When a member tries to book a class with no free places, no booking is created for them and the class's booked count stays equal to its capacity, even if a waitlist exists. The member is told the class is full.
Source: implied: U-1 and U-13; existing rule that classes are not overbooked

### C-2: A member who is told a class is full is offered the waitlist
Observable: In the same place where the member is told the class is full (the response to the booking attempt), joining the waitlist is presented as something they can do next. Wherever the app lists a full class for booking, the same option is available.
Source: request ("full classes don't turn people away")

### C-3: Joining the waitlist is a separate, deliberate action
Observable: A refused booking attempt on a full class does not by itself put the member on any waitlist; the member is on the waitlist only after they choose to join.
Source: choice: silently queueing a person who only tried to book would enrol them in something they did not ask for

### C-4: A member can join the waitlist of a full class
Observable: A member who is allowed to book the class, is not booked into it and is not on its waitlist, can join its waitlist while it has no free places. They are told they have joined and what their position is. They are not booked and the class's booked count does not change.
Source: request

### C-5: Positions are whole numbers counting from 1 in order of joining
Observable: The member at the front of the waitlist has position 1. A member who joins a waitlist with n members already on it has position n + 1. A member who joins an empty waitlist has position 1.
Source: implied: U-2, U-6

### C-6: Waitlists are first come, first served
Observable: Of the members waiting for a class, the one who joined earliest is the first to receive a free place. Nobody is moved ahead of an earlier joiner for any reason (for example membership type or how often they book).
Source: choice: the simplest order a member can understand and rely on

### C-7: There is no fixed limit on how many members can wait for a class
Observable: With 499 members waiting for a class, a further member can join and is told position 500; with 500 waiting, the next member can join and is told position 501.
Source: choice: the request names no limit and a limit would turn people away from the waitlist, which is what the request tries to avoid

### C-8: A member can see their own position at any time and it is current
Observable: For each class a member is waiting for, they can see their position. After a member ahead of them leaves the waitlist, or is booked, or is dropped from it, their displayed position is exactly one lower for each such member.
Source: implied: U-4

### C-9: Waiting is shown as different from being booked
Observable: A member's view of their classes distinguishes the classes they are booked into from the classes they are only waiting for. A class they are only waiting for is never presented as a confirmed booking.
Source: implied: U-4

### C-10: Waiting members do not count toward a class's capacity
Observable: A class with capacity N and N bookings and any number of waiting members reports N booked, and is still reported as full. The number of waiting members never changes the booked count.
Source: implied: C-1 and U-2

### C-11: Joining a waitlist is subject to every booking rule except "class has free places"
Observable: A member who the app would refuse to book today for any reason other than the class being full (whatever those rules are today) is refused when they try to join the waitlist, is told the reason, and is not added.
Source: implied: U-8(a)

### C-12: Only the member themselves can join or leave a waitlist for themselves
Observable: The same sign-in and permission rules that apply to booking and cancelling apply to joining and leaving a waitlist. A person who is not signed in, or who is signed in as someone else, cannot add or remove another member's waitlist entry; the attempt is refused and nothing changes.
Source: implied: existing rules on who can book and cancel

### C-13: Joining the waitlist uses up nothing the member would have to pay to book
Observable: Being on a waitlist does not use up any credit, pass, payment, or booking allowance that a booking would use up, and does not count against any limit on how many classes a member may be booked into. Whatever a booking uses up is used up at the moment the member is booked from the waitlist, and not before.
Source: implied: a place that is not yet held cannot be charged for

### C-14: A member who is already on the waitlist cannot join it again
Observable: Joining a waitlist already joined is refused with a reason, creates no second entry, and leaves the member's position unchanged.
Source: implied: U-7(a)

### C-15: A member who is already booked cannot join the waitlist for the same class
Observable: Joining the waitlist of a class the member is booked into is refused with a reason and the booking is unchanged.
Source: implied: U-7(b)

### C-16: A member cannot join the waitlist of a class that has free places
Observable: Joining the waitlist of a class that has at least one free place is refused with a reason that tells the member they can book it directly; no waitlist entry is created.
Source: choice: refusing is the loosest rule that still serves the member, who is told to book directly, and it keeps the waitlist from holding anyone who could simply be booked

### C-17: A member cannot join the waitlist of a class that can no longer be booked
Observable: Joining the waitlist of a class that has started, ended, been cancelled, or does not exist is refused with a reason and creates no entry.
Source: implied: U-7(d) and U-11

### C-18: A member can leave a waitlist
Observable: A member on a waitlist can withdraw. They are told they are no longer on it, they no longer appear as waiting, and they are not booked.
Source: implied: U-5

### C-19: Leaving moves the people behind up and leaves those ahead alone
Observable: When the member in position p leaves, each member who was at position greater than p is now one lower; each member at a position less than p keeps their position.
Source: implied: U-5 and C-8

### C-20: Leaving a waitlist one is not on is refused without side effects
Observable: Leaving a waitlist the member is not on is refused with a reason that says they are not on it; no one's position or booking changes.
Source: implied: U-7(e)

### C-21: Joining again after leaving puts the member at the back
Observable: A member who left a waitlist and joins it again is given the position at the end (n + 1 for n waiting), not their old position.
Source: choice: otherwise leaving and rejoining could be used to hold a place in line or jump ahead

### C-22: Waitlists of different classes are independent
Observable: A member may be on the waitlists of several classes at once, each with its own position; joining, leaving or being booked from one does not change their position on another.
Source: implied: members use the app for many classes

### C-23: When a booked place becomes free and someone is waiting, the first waiting member is booked
Observable: After a booked member cancels, or staff remove a booked member, and at least one member is waiting for that class, then without any further action by anyone, the waiting member who is first in line (and still allowed, see C-27) is booked into the class. The class is still full, and the cancelling member is no longer booked.
Source: request (the point of a waitlist)

### C-24: A member booked from the waitlist has an ordinary booking
Observable: The member appears among the class's booked members and counts toward its capacity, no longer appears as waiting, and can cancel the booking under the same rules that apply to any other booking.
Source: implied: U-3 and U-13

### C-25: A member booked from the waitlist is told
Observable: The member can find out that they were booked without looking for it: the next time they open their classes the new booking is there and the class is no longer shown as waiting. If the app sends a confirmation to members when they book a class, a member booked from the waitlist receives that same kind of confirmation.
Source: implied: U-3 (a place that nobody tells the member about is a place that goes unused)

### C-26: A free place goes to the waiting member, never to someone booking directly
Observable: While at least one eligible member is waiting for a class, a place that frees up is taken by the first of them. A different member who tries to book that class directly at the same moment, or later, is told the class is full (they may then join the waitlist) rather than being given the place.
Source: implied: U-9; without it, the order of the waitlist is not true

### C-27: A member who is no longer allowed to book is skipped, not booked
Observable: If, when a place frees up, the first member in line would be refused a booking for any reason other than the class being full (whatever those rules are at that time), they are not booked and the next member in line is considered, and so on down the list. If nobody waiting can be booked, the place stays free.
Source: implied: U-8(b)

### C-28: A skipped member is removed from the waitlist
Observable: A member skipped under C-27 no longer appears as waiting for that class and the members behind them move up one place each.
Source: choice: a member who cannot be booked would otherwise sit at the front and show a position that cannot become a booking

### C-29: Raising capacity fills the new places from the waitlist
Observable: When staff raise the capacity of a class by k places and at least k members are eligible and waiting, the first k eligible waiting members, in order, are booked. When fewer than k are waiting, all of them are booked and the remaining places are free for direct booking.
Source: implied: U-10(a)

### C-30: A freed place with nobody waiting behaves as it does today
Observable: When a booked member cancels a class that has no waitlist members, the place becomes free and the next member to book it is booked, as before.
Source: implied: U-6(c) and U-13

### C-31: Every freed place goes to exactly one member, exactly once
Observable: When k places are freed, no more than k members are booked from the waitlist, no member is booked into the same class twice, and each member who is booked is no longer shown as waiting.
Source: implied: U-9

### C-32: A class never holds more booked members than its capacity
Observable: However many members act at the same moment, including joins, cancellations, staff removals and direct bookings, the number of booked members of a class is never greater than its capacity.
Source: implied: U-9; existing rule that classes are not overbooked

### C-33: Positions on a waitlist are always distinct and run from 1 to the number waiting
Observable: At any moment, the members waiting for a class have positions 1, 2, ..., n with none repeated and none missing, including when several members join or leave at the same moment.
Source: implied: U-9

### C-34: When the class can no longer be booked, nobody is booked from its waitlist
Observable: From the moment a class has started (or earlier, at the time after which the app already refuses new bookings, if it has such a time), a place that frees up is not given to a waiting member; members still waiting are not booked, and no longer appear as waiting.
Source: implied: U-11

### C-35: When staff cancel a class, its waiting members are no longer waiting
Observable: After staff cancel a class, no member appears as waiting for it and no one is booked into it from the waitlist; the waiting members see the class as cancelled, as booked members do.
Source: implied: U-10(c)

### C-36: Staff can see who is waiting for a class and in what order
Observable: Wherever staff can see who is booked into a class, they can also see the members waiting for it, in position order, marked as waiting and not as booked. The number of booked members shown does not include them.
Source: choice: staff must be able to know who may arrive when places free up; limited to people who can already see the class's roster

### C-37: A member sees only their own position, not who else is waiting
Observable: A member's view of a waitlist shows their own position and no other member's name or contact details.
Source: choice: other members' identities are not needed for the member to use the waitlist

### C-38: Booking a class with free places is unchanged
Observable: A member who is allowed to book a class with at least one free place is booked as they are today, with the same result and the same rules applied.
Source: implied: U-13; existing rule that must be kept

### C-39: Cancelling a booking is unchanged for the member who cancels
Observable: A member cancels a booking under the same rules as today (including any cutoff time and anything refunded or restored) and with the same result for them, whether or not anyone is waiting for the class.
Source: implied: U-13; existing rule that must be kept

### C-40: Waitlists survive a restart
Observable: After the app is stopped and started again, every waitlist has the same members in the same order and each member's displayed position is unchanged.
Source: implied: U-12

### C-41: After a restart or return to service, places that should have been given out are given out
Observable: When the app starts and finds a class that can still be booked with free places and eligible members waiting, those places go to the waiting members in order, as in C-23, without anyone doing anything.
Source: implied: U-12 (a restart or version change can happen between a place freeing and it being filled)

### C-42: Existing data is untouched when the feature is introduced
Observable: When the new version is started on today's data, every existing class, booking and member is present and unchanged, the booked members of every class are the same, and every class has an empty waitlist.
Source: implied: U-12 (carry on with the data that exists today)

### C-43: The app starts with the settings used today
Observable: The new version starts and offers the waitlist with no new setting, and every setting used today has the same effect as before.
Source: choice: the request asks for no configuration and none is needed

### C-44: Returning to the previous version keeps every booking intact
Observable: If the previous version is started on the data after the new version has run (including after waitlist bookings were made), every booking, including bookings made from a waitlist, still shows in its class for the member as a normal booking, and no class, member or booking is missing or changed.
Source: implied: U-12 (going back to the version before)
