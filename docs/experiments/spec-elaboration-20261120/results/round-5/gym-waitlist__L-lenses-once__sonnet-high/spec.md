## Use cases

### U-1: A member joins the waitlist of a full class, to be given a place if one opens
Flow: The member, signed in, opens a class occurrence whose places are all taken. Instead of only a "full" dead end, they see a control to join the waitlist. They use it and are shown that they are on the waitlist and their position (the first person to join sees position 1). Joining costs them nothing.
Source: request ("full classes don't turn people away")

### U-2: A member checks where they stand on the waitlist
Flow: A waitlisted member opens the class, or the place where they see their own bookings, and sees that they are waitlisted and their current position. When people ahead of them leave or are given places, the position they see goes down accordingly.
Source: implied: a waitlist whose position cannot be seen leaves the member unable to decide whether to wait or make other plans

### U-3: A member leaves the waitlist
Flow: A waitlisted member uses a control to leave. They are shown that they are no longer on the waitlist, and the class again offers them the join control. People behind them move up one position.
Source: implied: anything a member can join they can change their mind about

### U-4: A member waiting is given a place when one opens
Flow: A booked member (or staff on their behalf) cancels, or capacity is increased. Without the waitlisted member doing anything, the earliest eligible waitlisted member becomes booked in the class. They are told, and the class now appears among their bookings.
Source: request ("waitlist ... so full classes don't turn people away")

### U-5: A waitlisted member who cannot take the place is passed over
Flow: A place opens, but the member at the front can no longer be booked (for example their membership has lapsed). They are removed from the waitlist and told; the place goes to the next eligible member, or, when nobody eligible is left, stays open for anyone to book directly.
Source: implied: U-4 gives a booking, and a booking is subject to the app's existing booking rules

### U-6: A member's attempt to join is refused
Flow: The member tries to join and cannot: the class is not full, they already hold a booking in it, they are already waitlisted, the waitlist has reached its limit, booking for the class has closed, the class does not exist, or they are not signed in. Each refusal tells them why in plain words, creates no entry, and changes nothing else.
Source: implied: every action has refusals and the member must be able to tell which one they hit

### U-7: A member's waitlist ends without a place
Flow: The class is cancelled, or the class reaches the time at which booking closes, while the member is still waiting. Their waitlist entry stops being active, they are never booked after that, and, if the class was cancelled, they are told.
Source: implied: a waitlist entry is state that must have an end

### U-8: Staff changes class capacity or removes a booking
Flow: Staff increases a class's capacity or removes a member's booking from a class that has people waiting. The places this frees go to the waitlist exactly as in U-4.
Source: implied: cancellations by members are not the only way a place opens

### U-9: Staff looks at who is waiting for a class
Flow: A staff user opens a class and sees the waitlist in order: each entry's member and when they joined. They can only look.
Source: implied: an operator running a class needs to see who is waiting; no change to the waitlist is requested for staff

### U-10: The feature is deployed onto, and can be rolled back from, a live system
Flow: The feature is released while classes, bookings and members already exist. Every existing booking is as it was; classes already full simply have an empty waitlist. If the release is reverted, bookings (including any that came from the waitlist) remain.
Source: implied: the request is for an existing app that already holds data

## Clauses

### C-1: A class occurrence is "full" exactly when the number of places taken equals or exceeds its capacity
Observable: In a class with capacity 10 and 10 bookings, the class is treated as full; at 9 bookings it is not. Places taken above capacity (possible if capacity was lowered) also counts as full.
Source: implied: request's "full classes"

### C-2: A full class offers a join-waitlist control to a signed-in member who is eligible to book and is neither booked nor waitlisted in it
Observable: Such a member opening a full class sees a control that joins the waitlist, where before this feature they could only see that the class is full.
Source: request

### C-3: A class that is not full offers no join-waitlist control, and a join request for it is refused
Observable: In a class with 9 of 10 places taken no join control is shown; a join request sent anyway (for example, from a page loaded while the class was full that has since had a place open) creates no entry and tells the member that a place is available and they can book it.
Source: implied: U-1, U-6; the waitlist exists for full classes

### C-4: A successful join creates exactly one waitlist entry for that member in that class and confirms it
Observable: After joining, the member sees that they are on the waitlist and their position; the class has one more waitlist entry; no booking exists for them in the class and no places taken change.
Source: request

### C-5: A member's position is 1 plus the number of active entries ahead of theirs
Observable: With an empty waitlist the first joiner sees position 1, the next 2, the next 3, and so on.
Source: implied: U-1, U-2

### C-6: Waitlist order is the order in which members joined, earliest first, and nothing else changes it
Observable: A member who joined at 09:00 is ahead of one who joined at 09:05 whatever the two members' tenure, plan or booking history; no joins ever share a position.
Source: choice: first-come first-served is the fairest rule and the one members assume when the request says nothing; no priority of any kind is requested

### C-7: Joining the same class's waitlist again while already on it leaves exactly one entry and the original position
Observable: Submitting the join twice (double click, two tabs) leaves one entry at the same position; the second submission tells the member they are already on the waitlist.
Source: implied: U-6; repeated submission of the same action

### C-8: A member who already holds a booking in a class cannot join its waitlist
Observable: The join is refused with a message saying they are already booked; no entry exists.
Source: implied: U-6

### C-9: Joining the waitlist is allowed only to a member who could book the class under the app's existing booking rules, other than the class being full
Observable: A member whose existing rules would stop them booking (the app's rules are not visible to this specification; at least an active account, an active membership or pass allowing the class, and any credits the app requires are assumed to be among them — unconfirmed) is refused at join with the same reason they would have been given for booking.
Source: implied: U-5, U-6; a member who could never be booked has no use for a place in the queue

### C-10: A class's waitlist holds at most 20 active entries
Observable: With 20 active entries, a 21st member's join is refused with a message that the waitlist is full, and no entry is created; the 20 entries and their positions are unchanged. After one entry leaves or is promoted, a join succeeds again and takes position 20.
Source: choice: a bound is needed so that positions stay meaningful and the state is finite; 20 is the decided value and has not been confirmed by the requester

### C-11: Joining closes when booking closes for the class
Observable: Once the app no longer lets a member book the class (at its existing booking cutoff, or at its start time where the app has no earlier cutoff), a join request is refused with a message saying booking has closed.
Source: implied: U-6, U-7; a waitlist for a class that cannot be booked has no purpose

### C-12: A join request for a class that does not exist is refused
Observable: The member is told the class cannot be found; nothing is created.
Source: implied: U-6; what a sentence names must exist

### C-13: A join request from someone who is not signed in is refused and sends them through the app's existing sign-in
Observable: No entry is created; after signing in, they are not auto-joined and must request the join again.
Source: implied: U-6; a waitlist entry belongs to a member

### C-14: A waitlist belongs to one occurrence of a class, not to a recurring class as a whole
Observable: A member waitlisted for Tuesday 18:00 has no entry for next Tuesday 18:00, and a place opening in one occurrence never promotes someone from another occurrence's waitlist.
Source: implied: the app books individual dated sessions and a place exists per session

### C-15: A member may be on the waitlists of any number of different classes at once
Observable: A member can join a second full class's waitlist while on the first; there is no refusal for holding several entries, including for two classes that overlap in time.
Source: choice: the request sets no limit, and a limit would turn people away

### C-16: Each waitlist entry is for one place
Observable: Joining never reserves or requests more than one place, and promotion creates one booking for one place.
Source: choice: the request implies one person one place; the app's treatment of guests or multi-place bookings is unknown

### C-17: A waitlisted member sees their own position on the class and in the place where they see their own bookings
Observable: In both places an entry reads as waitlisted and shows the current position as a number, in the class's view and in the member's list of their classes.
Source: implied: U-2

### C-18: The position a member sees is current as of the moment the page is viewed
Observable: When the member ahead at position 1 leaves, the member at position 2 sees position 1 the next time they view the class or their list, with no action beyond reloading.
Source: implied: U-2

### C-19: A member never sees who else is on a waitlist
Observable: No page or message addressed to a member shows another member's name, contact or account details through the waitlist; a member sees only their own position.
Source: implied: privacy of other members; only staff need identities (U-9)

### C-20: A waitlisted member can leave the waitlist, removing exactly their entry
Observable: After leaving, the member is shown they are off the waitlist, the join control is offered again (if the class is still full), and every entry that was behind theirs now shows a position one lower; entries ahead are unchanged.
Source: implied: U-3

### C-21: A leave request from someone with no active entry changes nothing and cancels nothing
Observable: A second leave submission, or a leave submitted after the member was promoted, tells the member that they are not on the waitlist (and, if they now hold a booking, that they are booked); their booking, if any, remains.
Source: implied: U-3; repeated or late submission

### C-22: A member who leaves and joins again takes the last position
Observable: Leaving at position 2 of 5 and joining again gives position 5 (or the next after the current last).
Source: choice: restoring a place would let people hold a place without waiting; the request is silent

### C-23: A member can leave only their own entry
Observable: A request to remove another member's entry (by any means a member can reach) is refused and the entry stays.
Source: implied: U-3; what a user may change

### C-24: Whenever places taken in a class drop below its capacity, the waitlist is offered the opening
Observable: The opening is offered, in each of these cases: a member cancels their booking; staff removes a member's booking; staff raises capacity; and any other event that makes places taken fewer than capacity (for example a booking being removed because an account was deactivated), while booking for the class is still open per C-11.
Source: request; implied: U-4, U-8

### C-25: Each opening goes to exactly one waitlisted member, the earliest on the list who is eligible, and no member is given more than one place by it
Observable: A capacity raised from 10 to 13 with 5 waiting books the first 3 eligible members in order and leaves the other 2 waiting at positions 1 and 2; a single cancellation books one member.
Source: request; implied: U-4

### C-26: A promoted member gets an ordinary booking in the class
Observable: The class appears in their bookings as a booking, counts towards the class's places taken, and their waitlist entry no longer shows.
Source: implied: U-4

### C-27: Promotion takes from the member whatever a direct booking would take, at the moment of promotion, and joining the waitlist takes nothing
Observable: If a booking uses one credit, the member's credits are unchanged on joining and drop by one on promotion; if booking costs nothing, nothing is deducted either time.
Source: implied: the request does not mention cost; a place on a waitlist is not a booking

### C-28: A waitlisted member who is not eligible at the moment of an opening is skipped, and their entry is removed
Observable: Eligibility is the same test as C-9 applied at that moment. The ineligible member has no booking and no waitlist entry afterwards, those behind move up, and the next entry is considered for the same opening.
Source: implied: U-5

### C-29: A member passed over under C-28 is told it happened and why
Observable: They receive a message, through the app's existing means of messaging members, naming the class and saying they were removed from the waitlist and the reason.
Source: implied: U-5; no silent removal

### C-30: When no waitlisted member is eligible for an opening, the place is open to direct booking
Observable: After every entry has been processed under C-28, the class shows as not full and any eligible member can book directly.
Source: implied: U-5

### C-31: While any waitlisted member is eligible, no one can book directly into an opened place ahead of them
Observable: With one member waiting and a cancellation in the class, a different member attempting to book directly immediately afterwards is told the class is full, because the waitlisted member already holds the place; no instant exists at which the opening is bookable directly.
Source: implied: U-4; interaction of waitlist and direct booking

### C-32: The cancellation (or the capacity increase, or other event) and the resulting promotions succeed or fail together
Observable: If the promotions cannot be completed, the member is told the action failed, the booking they tried to cancel is still held, the capacity is unchanged, and the waitlist is as it was.
Source: choice: an opening that no one is told about and that sits unfilled is worse than asking the person to try again

### C-33: Simultaneous openings fill distinct places and never over-fill
Observable: With 10 of 10 places taken and 3 waiting, two members cancelling at the same moment book the first two waitlisted members, never the same member twice, and places taken never exceeds 10 afterwards.
Source: implied: where the parts meet; two actions at once

### C-34: Simultaneous joins get distinct positions
Observable: Two members joining at the same moment onto a waitlist of 3 end up at positions 4 and 5, one each, and with 19 entries, two simultaneous joins result in one at position 20 and one refused under C-10.
Source: implied: where the parts meet

### C-35: A leave and a promotion that happen at the same moment resolve one way or the other, never both
Observable: Either the member is off the waitlist with no booking and the opening goes to the next eligible entry, or the member holds a booking and the leave is answered as in C-21; never off the waitlist with a booking lost, and never booked without an entry removed.
Source: implied: where the parts meet; one undone while the other runs

### C-36: A promoted member is told they now hold a place
Observable: They receive a message through the same means the app uses to confirm a direct booking, naming the class, its date and time, saying the place came from the waitlist, and saying how to cancel.
Source: implied: U-4; they were not present when it happened

### C-37: A failure to deliver a promotion message does not undo the booking
Observable: If the message cannot be delivered, the member's booking still exists and shows in their bookings.
Source: implied: runtime; message services can fail and are outside the booking's control

### C-38: When a class is cancelled, its waitlist ends and its members are told
Observable: Every active entry is removed, no promotion occurs, and each waitlisted member receives a message naming the class and saying it was cancelled; the class no longer appears among their waitlisted classes.
Source: implied: U-7

### C-39: An entry stops being active when booking closes for the class and no promotion occurs after that
Observable: After the C-11 moment, a booking cancelled in the class gives its place to no one; the member's list no longer shows the entry; positions are not offered; the class's staff view shows no active entries.
Source: choice: a place given at minutes' notice, after booking has closed, would not be bookable by the app's own rules

### C-40: A member who obtains a booking in the class through any path other than promotion has their entry removed
Observable: A member booked into a class by staff while on its waitlist has no waitlist entry afterwards, and those behind move up one.
Source: implied: where the parts meet; a member cannot hold a booking and an entry for the same class

### C-41: When a member's account is deactivated or deleted, their waitlist entries are removed
Observable: Entries for that member vanish from every waitlist; those behind move up; no place is offered to them.
Source: implied: state must have an end

### C-42: Staff can see a class's waitlist in order, with each entry's member and the time they joined
Observable: The staff view lists entries earliest first, matching the positions members see, for any class with an active waitlist, and shows an empty list when there are none.
Source: implied: U-9; choice: only a read view is provided, as the request asks for no management features

### C-43: Staff can only view the waitlist; they cannot add, remove or reorder entries
Observable: No control in the staff view adds, removes, reorders or promotes an entry; the staff reach the waitlist only through the actions in C-24.
Source: choice: deliberately left out because the request asks for no waitlist management

### C-44: Members cannot open the staff waitlist view
Observable: A member requesting it is refused and sees nothing of the list.
Source: implied: C-19

### C-45: Booking a class that is not full works as it did before this feature
Observable: A member booking a class with a free place gets a booking and the same confirmation and charge as before; no waitlist step appears.
Source: implied: must not change

### C-46: Places taken in a class never exceed its capacity because of the waitlist
Observable: No sequence of joins, leaves, cancellations and promotions raises places taken above capacity; a class with capacity 10 never shows 11 bookings that exist by promotion.
Source: implied: existing rule that a class has a capacity; must not change

### C-47: A booking that came from the waitlist is cancelled under exactly the same rules as any booking
Observable: Any existing cutoff, late-cancellation penalty or credit refund applies identically, with no extra grace for having been promoted late.
Source: implied: existing rules; choice: no special treatment is requested

### C-48: Releasing the feature leaves all existing bookings, classes and members unchanged
Observable: Counts and contents of bookings per class are identical before and after release; classes already full show the join control and an empty waitlist.
Source: implied: U-10

### C-49: Reverting the release leaves every booking, including those made by promotion, in place
Observable: After a revert, a member promoted earlier still holds their booking in the class; waitlist entries that existed are no longer acted on, and no booking is lost.
Source: implied: U-10; choice: waitlist entries need not survive a revert, bookings must
