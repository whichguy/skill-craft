## Use cases

### U-1: A member joins the waitlist of a full class, to keep a chance of getting in
Flow: The member looks at a class whose booked count equals its capacity (for example 10 booked of 10). The class is shown as full, with a way to join its waitlist instead of a dead-end refusal. The member joins. They see that they are on the waitlist and their position (1 if nobody is waiting, otherwise one more than the number already waiting). They are not booked.
Source: request

### U-2: A waitlisted member gets the spot when one opens, to attend without watching the app
Flow: Someone booked in the class cancels. The member first in line is booked into the class with no action of their own. The members behind them each move up one position. When the member next looks at their bookings, the class appears as booked, no longer as waiting.
Source: request

### U-3: A waitlisted member checks where they stand
Flow: The member opens their own bookings (or the class). For each class where they are waitlisted they see that they are waitlisted and their current position, which drops as people ahead of them are promoted or leave.
Source: implied: a waitlist is only useful if a member can see their place in it (U-1 shows a position)

### U-4: A waitlisted member leaves the waitlist, to stop waiting
Flow: The member chooses to leave the waitlist of a class. They are no longer on it and no longer shown as waiting. Members behind them move up one. If they later rejoin, they go to the back.
Source: implied: members' plans change; "waitlist" implies it is voluntary

### U-5: A member tries to join a waitlist when they cannot (unhappy paths)
Flow: The member tries to join the waitlist of a class (a) they are already booked in, (b) they are already waitlisted for, (c) that still has free spots, (d) that does not exist, or (e) that can no longer be booked for a reason other than fullness (for example it has already started). Each attempt is refused with a message saying why. Nothing changes: no booking, no new entry, no position change.
Source: implied: every action the request adds needs a defined refusal

### U-6: A member books a class that has free spots (existing behaviour, unchanged)
Flow: The member books a class with at least one free spot. They are booked immediately and the free-spot count drops by one. They are not put on any waitlist.
Source: implied: the request adds a waitlist for full classes only; ordinary booking must not change

### U-7: A member cancels a booking in a class that has a waitlist
Flow: The member cancels as they do today. Their booking is gone and they see what they see today. Behind the scenes the first waitlisted member takes the freed spot (U-2). The cancelling member does not need to do anything extra.
Source: implied: the spot a cancelling member frees is the event that makes the waitlist work

### U-8: A new member tries to book a class with a waitlist, right after a spot opens
Flow: A class is 10/10 with member A waiting. A booked member cancels, A is booked, and the class is 10/10 again. Member X, who is not on the waitlist, tries to book the class straight after. X finds the class full and is offered the waitlist; X does not get a spot ahead of the people waiting.
Source: implied: "waitlist" implies first come, first served; a spot opening must not be snatched past the queue

### U-9: Staff change a class in ways that free spots, or see who is waiting
Flow: Staff raise a class's capacity, or remove a member's booking, in the ways staff can already do this. Free spots appear and waitlisted members are booked in order to fill them. Staff who can see who is booked in a class can also see who is waiting, in order.
Source: implied: spots open by more than member cancellations, and staff need to see the waitlist to run a class

### U-10: Staff cancel or delete a class that has a waitlist
Flow: The class is cancelled or removed. Its waitlist entries are removed with it. No waiting member is promoted into it, and no member is left shown as waiting for a class that does not exist.
Source: implied: "carry on with the data that exists" – waitlist entries must not outlive their class

### U-11: A class starts while members are still waiting
Flow: A class has a waitlist and its start time passes. From then on nobody is promoted into it, even if a booked member cancels after it started. Members who were waiting are not shown as still waiting for it.
Source: implied: a spot freed after the class began is of no use to a waiting member

### U-12: A promoted member cannot actually be booked (unhappy path)
Flow: A spot opens and the member first in line would be refused by a rule that applies to bookings today (for example a clashing booking). That member is not booked and comes off the waitlist. The next member in line is considered for the spot.
Source: implied: promotion is a booking, so booking rules still bind; a stuck head of the queue must not block everyone behind

### U-13: Many people act at once, and the waitlist gets long (largest case)
Flow: Several members try to book the last free spot at the same moment, or several join the same waitlist at the same moment, or two booked members cancel at the same moment. The class is never over capacity, each waiting member has a distinct position, and nobody is promoted twice. A waitlist can grow to at least 100 members, and the 100th to join sees position 100.
Source: implied: a booking app is used by many people at once; a popular class is the very case the request is about

### U-14: A member is told they got in
Flow: A promoted member may not be looking at the app. If the app already sends members a message when they book a class, it sends the same kind of message when a member is promoted. If it sends none today, the member sees the booking the next time they open their bookings.
Source: implied: the member is booked without acting, so they need to find out

### U-15: An operator starts the new version on the data that exists today
Flow: The operator starts the version with the waitlist on an existing installation, with its existing classes and bookings and its existing configuration. The app starts without a manual data step or a new setting. Every existing class and booking is as it was. Every existing class starts with an empty waitlist, and members can join the waitlist of any that are full.
Source: implied: "carry on with the data that exists today"

### U-16: An operator restarts the app while members are waiting
Flow: The operator stops and starts the app. Every waitlist has the same members in the same order, with the same positions, as before.
Source: implied: a waitlist that forgets its queue on restart would turn people away silently

### U-17: An operator goes back to the version before the waitlist
Flow: The operator returns to the previous version, keeping the data the new version has been writing. It starts and runs. Every class and booking is intact, including bookings made by promotion. Members who were still waiting are not booked into anything.
Source: implied: "go back to the version before"

### U-18: A member or staff member acts without permission
Flow: A person who is not signed in, or who is signed in as another member, tries to join or leave the waitlist for a member who is not themselves. The attempt is refused as other such booking attempts are, and no waitlist changes.
Source: implied: the waitlist is another way to act on a member's bookings, and the app already limits who may do that

## Clauses

### C-1: A full class offers a way to join its waitlist
Observable: For a class with capacity 10 and 10 booked, the class is shown to a member as full with a way to join its waitlist. A member who uses it ends up on the waitlist of that class. The booked count stays 10.
Source: request

### C-2: A booking attempt on a full class does not silently join the waitlist
Observable: When a member tries to book a class that has 0 free spots, they are told the class is full and that the waitlist is available. They are not booked, and they are not added to the waitlist until they join it themselves.
Source: choice: joining is a commitment to a queue and a possible later booking; making it an explicit member action is the loosest rule that still stops people being turned away

### C-3: Waitlist order is order of joining
Observable: Members A, B and C join the same waitlist in that order. A is at position 1, B at position 2, C at position 3. Positions count from 1.
Source: implied: U-1 shows a position, and "waitlist" implies first come, first served

### C-4: A new entry goes to the end and its position is shown on joining
Observable: With 3 members already waiting, a member who joins is told they are at position 4. With nobody waiting, a member who joins is told they are at position 1.
Source: implied: U-1 (the member needs to know their place)

### C-5: Waiting members do not count as booked
Observable: A class with capacity 10 and 10 booked, with 5 members waiting, still shows 10 booked and 0 free spots, and the list of members booked in the class does not include the 5 waiting.
Source: implied: U-1 (a waitlist entry is not a booking)

### C-6: A cancellation in a class with a waitlist books the first waiting member
Observable: In a class that is 10/10 with A, B, C waiting in that order, a booked member cancels. A is booked in the class and is no longer on its waitlist. The class is 10/10. B is at position 1 and C at position 2.
Source: request

### C-7: Promotion needs no action from the member
Observable: The promoted member is booked without accepting, confirming or claiming anything, and without any time limit running against them. Their bookings show the class as booked as soon as a spot opens and they next look.
Source: choice: an accept-or-lose window needs timers and leaves the spot empty meanwhile; automatic booking serves the member and the class with the least machinery

### C-8: Members behind a removed entry each move up by one and keep their relative order
Observable: With A, B, C, D waiting at positions 1 to 4, B leaves the waitlist: A stays at 1, C becomes 2, D becomes 3. If instead A is promoted, B becomes 1, C 2, D 3.
Source: implied: U-3 (a position that drops as people ahead go)

### C-9: A waiting member can see their own waitlist status and position
Observable: A member waiting at position 3 in a class sees, among their own classes, that they are waiting for it and that their position is 3. After the member at position 1 leaves, they see 2.
Source: implied: U-3

### C-10: A member can leave a waitlist
Observable: A waiting member leaves the waitlist of a class. They are no longer shown as waiting for it, and the class's waitlist has one fewer entry.
Source: implied: U-4

### C-11: Rejoining after leaving goes to the back
Observable: A is at position 1 of 3. A leaves, then joins again. A is at position 3.
Source: implied: U-4 (first come, first served is by time of joining, not by history)

### C-12: Leaving a waitlist you are not on is refused without change
Observable: A member who is not waiting for a class asks to leave its waitlist. They are told they are not on it. No waitlist changes.
Source: implied: U-5 (every added action needs a refusal)

### C-13: A member already booked in the class cannot join its waitlist
Observable: A member booked in a full class tries to join its waitlist. The attempt is refused with a message saying they are already booked. They stay booked and no entry is created.
Source: implied: U-5 (a)

### C-14: A member already on the waitlist cannot join it twice
Observable: A member at position 2 of a waitlist tries to join it again. The attempt is refused with a message saying they are already waiting. They remain at position 2 and the waitlist has the same number of entries as before.
Source: implied: U-5 (b)

### C-15: A class with free spots has no waitlist to join
Observable: A member tries to join the waitlist of a class that is 9/10. The attempt is refused with a message saying the class has free spots and can be booked directly. No entry is created.
Source: choice: refusing is the loosest rule that keeps a free spot and a queue from existing together; the member can book straight away

### C-16: Joining is refused whenever booking would be refused for a reason other than fullness
Observable: A member tries to join the waitlist of a class that does not exist, or of a class that has already started (or is otherwise closed to booking under the rules for booking today). The attempt is refused with a message saying why. No entry is created.
Source: implied: U-5 (d) and (e)

### C-17: A member joins or leaves only their own waitlist entries
Observable: A person who is not signed in, or who is signed in as member M, cannot add or remove a waitlist entry for member N. The attempt is refused in the way a booking attempt for another member is refused today, and the waitlist is unchanged.
Source: implied: U-18

### C-18: Staff who can see a class's bookings can see its waitlist in order
Observable: For a class with A, B, C waiting, staff see the waiting members as A, B, C in that order, apart from the booked members.
Source: choice: staff run the classes and have to see who is waiting; showing the waitlist where bookings are shown adds nothing new

### C-19: Any increase in free spots books waiting members in order
Observable: Staff raise a class's capacity from 10 to 13 while 5 members wait: the first 3 in line are booked, and the other 2 are at positions 1 and 2. Staff remove one member's booking while 2 wait: the first in line is booked and the other is at position 1. In both cases the waitlist shrinks by exactly the number of spots that opened, or to 0 if it was shorter.
Source: implied: U-9 (the waitlist must fill spots however they open)

### C-20: A new booking cannot take a spot ahead of waiting members
Observable: A class is 10/10 with A waiting. A booked member cancels and A is booked, making the class 10/10 again. Member X, who is not waiting, tries to book that class and finds it full; X is not booked.
Source: implied: U-8

### C-21: Becoming booked by any means removes that member's waiting entry for the class
Observable: A member waiting in a class is booked into it in a way that is not promotion (for instance by staff). They are shown as booked, they are not shown as waiting for it, and members behind them move up.
Source: implied: a member cannot be both booked and waiting (C-13)

### C-22: Promotion is subject to the rules that govern booking today
Observable: A member first in line who would be refused a booking by an existing booking rule (for example a clashing booking at the same time) is not booked.
Source: implied: U-12

### C-23: A member who cannot be booked at promotion is dropped and the next in line is tried
Observable: A, B waiting; a spot opens; A would be refused by an existing booking rule. A is not booked and is no longer waiting. B is booked.
Source: choice: dropping the blocked member is the loosest rule that keeps a blocked head of the queue from holding the spot

### C-24: No promotion happens into a class that can no longer be booked
Observable: A class started at 18:00 with member A waiting. A booked member cancels at 18:05. A is not booked, and the class is not over capacity.
Source: choice: a spot freed after the class starts is of no use; the cutoff follows the existing rule for when a class can no longer be booked

### C-25: A member is not shown as waiting for a class that can no longer be booked
Observable: After a class has started, members who had been waiting for it do not see it listed as one they are still waiting for.
Source: choice: an eternal "position 2" for a class that is over is misleading

### C-26: Cancelling or deleting a class removes its waitlist
Observable: A class with 3 waiting members is cancelled or deleted. None of the 3 is booked into it, and none sees it as a class they are waiting for.
Source: implied: U-10

### C-27: A promoted member is notified by whatever channel the app already uses for booking confirmations
Observable: If the app sends a member a message when they book a class, a promoted member gets a message of the same kind saying they have been booked in the class. If the app sends no such message, no new message is required.
Source: choice: no new channel is added; a promoted member who is not looking at the app still learns of it where the app already tells members about bookings

### C-28: Booked count never exceeds capacity when requests arrive at once
Observable: A class has 1 free spot and 5 members try to book it at the same moment. Exactly 1 is booked; the other 4 are told the class is full and offered the waitlist. The class has the same number of booked members as its capacity.
Source: implied: U-13, and the existing rule that a class cannot be over capacity (C-35)

### C-29: Members joining a waitlist at once get distinct positions
Observable: 5 members join an empty waitlist at the same moment. Their positions are 1, 2, 3, 4 and 5, each used once.
Source: implied: U-13

### C-30: Simultaneous cancellations promote different members, once each
Observable: A class is 10/10 with A, B, C waiting. Two booked members cancel at the same moment. A and B are booked, each once, and C is at position 1. The class is 10/10.
Source: implied: U-13

### C-31: A waitlist can hold at least 100 members
Observable: 100 members join the waitlist of one full class. Every join succeeds, and the 100th to join is told they are at position 100. A booked member then cancels: the member at position 1 is booked, and the one who was at position 100 is at position 99.
Source: choice: the request names no limit; a waitlist is useless if it is capped low, so a floor of 100 is fixed and no refusal for length is required below it

### C-32: Waitlists survive a restart
Observable: With A, B, C waiting in a class, the operator stops and starts the app. A, B, C are still waiting, in that order, at positions 1, 2, 3.
Source: implied: U-16

### C-33: Existing classes and bookings are unchanged when the waitlist version starts
Observable: Before and after the first start of the new version on an existing installation, every class has the same details and capacity, and every member has the same bookings.
Source: implied: U-15

### C-34: The new version starts without a manual data step
Observable: The operator starts the new version on an installation created by the previous version, with no migration command or data edit. The app starts and serves requests.
Source: implied: U-15

### C-35: The new version starts with the existing configuration unchanged
Observable: The operator starts the new version using the configuration the previous version used, with no new setting added. The waitlist is available to members.
Source: implied: U-15

### C-36: Every class starts with an empty waitlist after the upgrade
Observable: Right after the upgrade, every class (including any that is full) has no one waiting. A member can join the waitlist of a full class and gets position 1.
Source: implied: U-15

### C-37: The previous version can run on the data the new version wrote
Observable: The operator starts the previous version on the data after the new version has run, with waitlists in use. The previous version starts. Every class is still there, every booking is still there (including bookings made by promotion), and no member who was waiting and not promoted is booked in any class.
Source: implied: U-17

### C-38: Booking a class with free spots works as before
Observable: A class is 9/10. A member books it. They are booked at once, the class is 10/10, and they are not placed on any waitlist.
Source: implied: U-6

### C-39: A class never has more booked members than its capacity
Observable: However many members book, cancel, join or leave waitlists, or are promoted, the number booked in a class is never more than its capacity.
Source: implied: U-6 (existing rule that a full class is full)

### C-40: A member cannot hold two bookings in the same class
Observable: A member already booked in a class tries to book it again. The attempt is refused as it is today and they have one booking.
Source: implied: U-6 (existing rule, to be kept)

### C-41: Cancelling a booking works as before for the member who cancels
Observable: A member cancels a booking in a class that has 3 members waiting. The member sees the same result, applies the same cancellation rules and gets the same message as they would for a class with nobody waiting.
Source: implied: U-7

### C-42: Classes with nobody waiting behave exactly as before
Observable: For a class with an empty waitlist, listing, booking, cancelling and the free-spot count behave as before the waitlist existed.
Source: implied: U-6 and U-15 (what must not change)
