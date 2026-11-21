## Use cases

### U-1: A member joins the waitlist of a full class, to be let in if a place opens
Flow: The member opens a class that is full. Where the class's waitlist is open to them they see a "join waitlist" action instead of a "book" action. They take it and see that they are on the waitlist and their position (1 = next in line).
Source: request

### U-2: A member checks where they stand on the waitlists they have joined
Flow: The member opens their own list of waitlists (or the class itself) and sees, for each upcoming class they are waiting for, the class, its start time and their current position.
Source: implied: a waitlist the member cannot look at gives them no way to know whether to make other plans.

### U-3: A member leaves a waitlist they no longer want to be on
Flow: The member takes the "leave waitlist" action on the class and sees they are no longer on it. Those behind them move up one place.
Source: implied: any list a person can join, a person can leave.

### U-4: A waitlisted member is given the place when one opens
Flow: A booked member cancels (or capacity is raised, or staff remove a booking). The first member in line is booked into the class without doing anything, is told by email, and sees the class in their bookings.
Source: request ("so full classes don't turn people away")

### U-5: A waitlisted member who cannot be booked at the moment a place opens is passed over
Flow: When it is a member's turn but the booking cannot be made for them, they are removed from the waitlist, told why, and the place goes to the next member in line.
Source: implied: U-4 assumes every member in line can be booked when their turn comes.

### U-6: A member without a waitlist in play books and cancels exactly as before
Flow: A member books a class with free places, or cancels a booking, as they do today. Nothing about this changes except that a freed place goes to the waitlist first.
Source: implied: the request adds a feature to an existing booking app; existing booking must keep working.

### U-7: Staff view who is waiting for a class
Flow: A staff member opens a class and sees its waitlist in order: who is waiting, since when, in what position.
Source: implied: staff who run a class need to know how much demand it has.

### U-8: Staff remove someone from a waitlist
Flow: A staff member removes a named member from a class's waitlist; the member is told and those behind move up.
Source: implied: staff manage who is on their classes.

### U-9: Staff configure the waitlist of a class
Flow: A staff member turns the waitlist on or off for a class and sets how many people it may hold.
Source: implied: a waitlist with no limit and no switch cannot be run.

### U-10: Staff change a class that has a waitlist (raise capacity, cancel it, move it)
Flow: Staff raise capacity: people are let in from the waitlist. Staff cancel the class: the people waiting are told. Staff change its time: the people waiting are told.
Source: implied: classes are changed by staff after people have joined waitlists for them.

### U-11: A promoted member decides they cannot come
Flow: The member cancels the booking they were given from the waitlist, as for any booking; the place goes on to the next member in line.
Source: implied: U-4 books people without asking them first.

### U-12: The operator ships the feature, and could go back
Flow: The feature is deployed over an app with existing classes and bookings; nothing existing is lost or changed in meaning. If the feature is rolled back, bookings made by the waitlist stay valid.
Source: implied: the app has live data when this is added.

### U-13: The operator looks back at what happened on a waitlist
Flow: Staff open the history of a class's waitlist and see each join, leave, promotion, removal and pass-over with its time.
Source: implied: members will ask "why was I not let in?".

### U-14: Someone who may not join a waitlist tries to, and is told why
Flow: A visitor who is not signed in, a member whose account or membership does not allow booking, or a member looking at a class that has started or been cancelled, takes the join action (or is shown the class) and is told why they cannot join; nothing is created.
Source: implied: "full classes don't turn people away" takes for granted that the person is someone the class could take.

### U-15: A waiting member's account goes away
Flow: A member's account is removed (by them or by staff) while they are on one or more waitlists; they drop off those waitlists and those behind move up.
Source: implied: the request takes for granted that a waitlisted person continues to exist.

## Clauses

### C-1: A class is full when its active bookings equal or exceed its capacity
Observable: A class with capacity 12 and 12 active bookings is shown as full; the same class with 11 active bookings is shown as bookable; a class with capacity 12 and 13 active bookings (capacity lowered after booking) is shown as full.
Source: implied: "full classes"

### C-2: A waitlist belongs to one dated session of a class, not to a recurring series
Observable: A member on the waitlist for the Monday 18:00 session is not on the waitlist for the following Monday 18:00 session and is not offered a place in it.
Source: choice: bookings are made for a specific session; the loosest reading that keeps promotion from booking someone into a date they never chose.

### C-3: Where a class is full and its waitlist is open to the member, the member is offered "join waitlist" instead of "book"
Observable: On the page of a class that counts as full (C-26) whose waitlist is on and has room, a member who is not booked, not already waiting, and may join (C-42) sees a join-waitlist action and no working book action.
Source: request

### C-4: Joining the waitlist adds the member at the end of the waitlist and shows their position
Observable: Joining an empty waitlist shows position 1; joining a waitlist with 3 people on it shows position 4.
Source: request

### C-5: The waitlist is first come, first served by time of joining
Observable: Members A, B, C join in that order; when one place opens, A is booked; when the next opens, B is booked; C is never booked ahead of A or B.
Source: implied: "waitlist"

### C-6: A member sees their own position on the class and in their list of waitlists
Observable: A member in position 3 sees "3" for that class on the class page and in their waitlists list.
Source: implied: U-2

### C-7: A member's position goes down by one when someone ahead of them leaves, is removed, or is promoted
Observable: Member in position 3; the member in position 1 is promoted; on the next view the member is in position 2.
Source: implied: U-2, U-3

### C-8: Joining is refused when the class does not count as full
Observable: A member who requests to join the waitlist of a class with 11 of 12 places taken and no one waiting is not added and is told that a place is available to book.
Source: implied: a waitlist is for full classes; joining when a place is free would book them without their having asked.

### C-9: Joining is refused when the member already holds a booking in that class
Observable: A booked member who requests to join the waitlist of that class is not added and is told they are already booked.
Source: implied: U-1

### C-10: Joining twice leaves one entry
Observable: A member who requests to join the same waitlist twice (e.g. a double click) is on it once, with one position, and is told they are already on it and at what position.
Source: implied: U-1 repeated

### C-11: Each class has a waitlist capacity that defaults to 10
Observable: A class never edited by staff accepts 10 waitlist entries and refuses the 11th.
Source: choice: a bound is needed; 10 is a size a front desk can manage.

### C-12: Joining a waitlist that is at its capacity is refused
Observable: With 10 of 10 waitlist places used, a join request adds no entry and the member is told the waitlist is full.
Source: implied: C-11

### C-13: A member can leave a waitlist they are on
Observable: After "leave waitlist" the member's entry is gone from the class page and their waitlists list, and, where C-3 holds, the member is offered the join action again.
Source: implied: U-3

### C-14: Leaving a waitlist you are not on has no effect and is not an error
Observable: A second leave request (double click, stale page) leaves the waitlist unchanged and tells the member they are not on it.
Source: implied: U-3 repeated

### C-15: A member who leaves and rejoins goes to the end of the waitlist
Observable: Member in position 1 leaves and rejoins a waitlist of 4 others: they are now position 5.
Source: choice: keeping the old position would let members hold a place without being on the list.

### C-16: When a place opens and the waitlist has someone, the first person in line is booked into the class
Observable: Class full with waitlist [A, B]. A booked member cancels. Within the time in C-24 A has a booking for the class, A is no longer on the waitlist, B is in position 1, and the class is full.
Source: request

### C-17: A booking made from the waitlist is an ordinary booking
Observable: It appears in the member's bookings alongside others and can be cancelled the same way; its cancellation rules are those of any booking in that class.
Source: implied: U-11

### C-18: A place opens, for waitlist purposes, whenever active bookings fall below capacity, by any of these four routes: a member cancels their booking; staff cancel a member's booking; a booking ends because the member's account is removed; staff raise the capacity
Observable: In each of the four cases, with the class otherwise full and the waitlist non-empty, the first person in line is booked, once per place opened. A booking made from the waitlist that is later cancelled opens a place by the first route.
Source: implied: "so full classes don't turn people away"

### C-19: When several places open at once, that many people are booked, in order
Observable: Capacity raised from 12 to 14 with waitlist [A, B, C]: A and B are booked, C is in position 1.
Source: implied: U-10

### C-20: When a member is booked from the waitlist, they are told by email
Observable: An email to the member's account address contains: the class name; its start date and time in the class's local time; the class's location where the class has one; a statement that the member now has a booking; how to cancel it; and, where the app has a cancellation cutoff, the cutoff.
Source: choice: the request does not name a channel; email is the channel that reaches a member who is not in the app.

### C-21: The member sees a waitlist-promoted booking in their bookings
Observable: The class appears in their bookings, whether or not the email is delivered.
Source: implied: C-20 can fail.

### C-22: A member is passed over, removed from the waitlist, and the place goes to the next in line, if the booking cannot be made for them when their turn comes
Observable: A is first in line, with no valid membership (see C-23). A place opens; A is removed from the waitlist, B (second) is booked.
Source: implied: U-5

### C-23: A member cannot be booked when any of these holds at the moment of their turn: their account is removed or suspended; their membership or plan does not cover the class; they lack the credit or payment the existing booking requires; they already hold a booking in the class; any other condition on which the existing booking flow refuses them
Observable: A member in each of these states, first in line, is passed over (C-22); a member in none of them is booked.
Source: implied: U-5 ; the list of existing refusal conditions is unconfirmed because the existing booking flow is not visible to this specification.

### C-24: A booking from the waitlist is visible to the member within 60 seconds of the place opening
Observable: 60 seconds after a booked member cancels a full class with a waitlist, the first waiting member's bookings list shows the class, whether or not anyone has opened the app in the meantime.
Source: choice: members must be able to rely on it before the class; the figure is chosen, not given.

### C-25: A member who is passed over is told, and told that they are no longer on the waitlist
Observable: A message to the member names the class and its start date and time, states they are no longer on the waitlist, states they were not booked, and says which of the conditions of C-23 applied.
Source: implied: U-5

### C-26: A place that someone on the waitlist is waiting for counts as taken, so a class with anyone on its waitlist counts as full, for booking and for joining
Observable: Class full, waitlist [A]. A booked member cancels. Member Z requests to book at the same instant: Z is told the class is full and is not booked; A is booked; Z may then join the waitlist and is in position 1. A join request by Z in the same moment, before A is booked, adds Z behind A.
Source: implied: C-5

### C-27: A class with an empty waitlist books members as before
Observable: Class with 11 of 12 places and no waitlist: a member who books is booked at once, with no waitlist step.
Source: implied: U-6

### C-28: Joining the waitlist is free
Observable: Joining takes no credit or payment and a member who leaves is not charged.
Source: choice: charging happens when a place is actually obtained.

### C-29: Where the existing app takes credit or payment for a booking, it is taken when the member is booked from the waitlist
Observable: A credit-based member promoted from the waitlist has one credit fewer after promotion than before it, and the same as before if they joined and left.
Source: choice: consistent with C-28.

### C-30: The waitlist closes when the class starts
Observable: At the class's start time, the waitlist accepts no joins and no one is booked from it; entries still on it end and no longer appear in members' waitlists list.
Source: choice: a place at a class already under way is of no use to the person waiting.

### C-31: When staff cancel a class, everyone on its waitlist is removed and told
Observable: Each waiting member receives a message naming the class and its start date and time and stating it is cancelled; the waitlist is empty.
Source: implied: U-10

### C-32: When staff change a class's start time, waiting members stay on the waitlist and are told the new time
Observable: Each waiting member receives a message stating the class and its new start date and time; positions are unchanged.
Source: choice: the member can leave if it no longer suits.

### C-33: Staff see a class's waitlist in order, with each member's name, time of joining, and position
Observable: Waitlist [A at 09:01, B at 09:05] shows A as 1 with 09:01 and B as 2 with 09:05.
Source: implied: U-7

### C-34: Staff can remove a member from a waitlist
Observable: The member is no longer on the waitlist and those behind move up one.
Source: implied: U-8

### C-35: A member removed by staff is told
Observable: A message names the class and its start date and time and states they were removed from the waitlist.
Source: choice: the member should not be left waiting silently.

### C-36: Staff can turn the waitlist of a class on or off
Observable: With the waitlist off, a full class shows no join action to members; turned on again, a full class with room shows it (C-3).
Source: implied: U-9

### C-37: Only staff can see the names on a waitlist
Observable: A non-staff member who requests the staff waitlist view, or another member's entry, is refused and sees no names.
Source: implied: U-7, C-46

### C-38: A history of each class's waitlist is kept and visible to staff
Observable: For each of these nine events there is a line with time, member and event: joined; left; promoted; passed over (with the condition of C-23 that applied); removed by staff; class cancelled; waitlist closed at start; account removed; booked by another route.
Source: implied: U-13

### C-39: Deploying the feature leaves existing classes, bookings and members unchanged
Observable: Before and after deployment, every class has the same capacity and the same bookings, every member has the same account and credit, and every class has an empty waitlist.
Source: implied: U-12

### C-40: Bookings made from the waitlist remain valid if the feature is rolled back
Observable: After rollback, a member promoted earlier still sees and can cancel their booking.
Source: implied: U-12

### C-41: Only a signed-in member can join or leave a waitlist
Observable: A visitor who is not signed in and takes the join action is asked to sign in and no waitlist entry is created.
Source: implied: U-14; an entry belongs to a member.

### C-42: Joining is refused for a member whose account is suspended or whose membership or plan does not cover the class
Observable: A member in either state who requests to join is not added and is told which of the two applies.
Source: choice: refusing at joining spares the member waiting for a place that C-23 would then refuse them.

### C-43: Lack of credit or payment does not stop a member joining
Observable: A member with 0 credits who requests to join a waitlist is added; credit is checked only when their turn comes (C-23).
Source: choice: the member may top up while waiting.

### C-44: Joining is refused for a class that has been cancelled or has started
Observable: A join request for a class whose start time has passed, or which staff have cancelled, adds no entry and tells the member which of the two applies.
Source: implied: U-14, C-30

### C-45: The confirmation of joining tells the member two things: that they will be booked automatically, with no further action from them, if a place opens; and that a place is not guaranteed
Observable: After joining, the confirmation conveys both statements.
Source: implied: U-1; a member who does not know they are booked automatically may book elsewhere or wait for an invitation that never comes.

### C-46: Members cannot see who else is on a waitlist
Observable: On a full class page and in the waitlists list, a member sees no name, email address or other identifying detail of any other member on the waitlist.
Source: implied: members' details are private to the app and its staff.

### C-47: A full class that offers no join action tells the member why
Observable: A full class with the waitlist off shows that the waitlist is not offered; a full class with 10 of 10 waitlist places used shows that the waitlist is full; neither shows a join action.
Source: implied: "don't turn people away" — a refusal must at least say what it is.

### C-48: Turning the waitlist off for a class stops new joins only; members already waiting stay on it and are still booked from it as places open
Observable: Class with waitlist [A, B]; staff turn the waitlist off; a join request by C is refused; a place opens; A is booked.
Source: choice: removing people already waiting would turn away the people the request set out to serve.

### C-49: Lowering a waitlist's capacity below the number already waiting removes no one
Observable: 8 waiting, capacity lowered to 5: all 8 stay and stay in order; a join request is refused until fewer than 5 are waiting.
Source: choice: as C-48.

### C-50: Lowering a class's capacity below its active bookings cancels no booking and no one is booked from the waitlist until active bookings are below the new capacity
Observable: Capacity 12 lowered to 10 with 12 bookings and waitlist [A]: the 12 stay booked; after two of them cancel (10 bookings) A is not booked; after a third cancels (9 bookings) A is booked.
Source: implied: C-1; the waitlist must not take a class past its capacity.

### C-51: A waitlist entry stands for one place
Observable: A member booked from the waitlist holds one place, and one place is taken from the count of free places.
Source: choice: the request offers no way to ask for more than one; where the existing app lets a member book for several people, the waitlist does not.

### C-52: When a member's account is removed, their waitlist entries are removed
Observable: A member on 3 waitlists whose account is removed is on none of them; each member behind them has moved up one place.
Source: implied: U-15

### C-53: A member with no usable email address is still booked from the waitlist
Observable: A first-in-line member whose account has no email address is booked, sees the booking in the app, and no error is raised to the canceller or to staff.
Source: implied: C-20, C-21

### C-54: Waitlist messages are sent whatever the member's marketing or notification preferences
Observable: A member who has turned off marketing email still receives the booked, passed-over, removed, cancelled and time-change messages of C-20, C-25, C-31, C-32 and C-35.
Source: choice: they concern a booking the member relies on, not promotion.

### C-55: Times on waitlist pages and in waitlist messages are the class's local time
Observable: A class in a location whose local time is 18:00 is shown and mailed as 18:00 to a member who is in another time zone.
Source: choice: a class is attended in the place it is held.

### C-56: A class with capacity 0 is full, and its waitlist works as for any full class
Observable: A class with capacity 0 shows as full; joining follows C-3 and C-11; no one is booked from it until capacity is raised.
Source: implied: C-1

### C-57: Where the existing app takes a booking inside a cancellation cutoff, the cutoff is measured from the class's start, not from when the member was booked from the waitlist
Observable: A member booked from the waitlist 30 minutes before a class whose cutoff is 120 minutes is treated, if they cancel, as any member who cancelled 30 minutes before.
Source: choice: C-17; consistency with ordinary bookings.

### C-58: Concurrent cancellations each open a distinct place, and each place goes to a different member in order
Observable: Waitlist [A, B, C]; two booked members cancel at the same moment; A and B are each booked once, C is in position 1, and the class has 12 bookings out of 12.
Source: implied: U-4 with U-6 at once.

### C-59: Concurrent joins never exceed the waitlist's capacity and never produce two entries with the same position
Observable: Waitlist capacity 10 with 9 waiting; 5 members request to join in the same moment; exactly one is added, at position 10; the other four are told the waitlist is full.
Source: implied: C-11, C-12, C-4

### C-60: A cancellation requested twice opens one place
Observable: A member who cancels by double-clicking, or a cancellation request that is delivered twice, opens one place: one member is booked from the waitlist.
Source: implied: C-18 with a repeated action.

### C-61: A leave request and a promotion of the same entry at the same moment end the entry once
Observable: If the leave takes effect first, the member is not booked and the next in line is. If the promotion takes effect first, the member is booked, and the leave request tells them they are booked and not on the waitlist; the booking stands.
Source: implied: C-13 with C-16.

### C-62: A staff removal and a promotion of the same entry at the same moment end the entry once
Observable: If the removal takes effect first, the member is told they were removed, and the next in line is booked. If the promotion takes effect first, staff are told the member has been booked, and nothing is removed.
Source: implied: C-34 with C-16.

### C-63: A class cancellation and a promotion at the same moment end in one consistent state
Observable: Either no booking is made and the waiting member receives only the cancellation message of C-31, or a booking is made and then cancelled with the class and the member receives only the cancellation message of C-31 (and no "you are booked" message).
Source: implied: C-31 with C-16.

### C-64: At and after the class's start instant, no one is booked from the waitlist and no one joins it
Observable: A cancellation processed at 18:00:00 for a class that starts at 18:00:00 books no one from the waitlist; a cancellation at 17:59:59 books the first in line.
Source: implied: C-30; a rule with a boundary must say which side the boundary is on.

### C-65: A system failure while booking someone from the waitlist leaves their entry and position unchanged and the booking is retried until it succeeds or the class starts
Observable: With the booking step failing for the first attempt only, A (first) is still position 1 afterwards, B is not booked in A's place, and A is then booked.
Source: implied: C-16; a failure of the app is not a failure of the member (compare C-22).

### C-66: A booking from the waitlist happens once and costs once, however many times it is attempted
Observable: After a retried promotion, A has one booking in the class and has had one credit taken (where credits apply).
Source: implied: C-65, C-29

### C-67: A message for one waitlist event is sent once when it is delivered, and re-attempted until it is delivered or the class starts when it is not
Observable: A delivery failure for A's "you are booked" email is retried; once delivered, no second copy is sent; after the class starts, no further attempts are made.
Source: choice: C-20 depends on delivery; the retry period is bounded by the point at which the message stops being of use.

### C-68: A failed or slow message to one member does not delay another member's booking
Observable: With A's email provider call failing, B (second in line) is booked within the time of C-24 when a second place opens.
Source: implied: C-21

### C-69: A member on the waitlist who becomes booked into that class by any other route leaves the waitlist
Observable: Member A is on the waitlist; staff book A on their behalf (or A obtains the place by any other route); A has one booking and is not on the waitlist; A is not booked twice and is charged once where charging applies.
Source: implied: C-9; a member is never both booked and waiting.

### C-70: The rule that a new booking cannot take a place the waitlist is waiting for applies to every route by which a booking is made, including bookings made by staff on a member's behalf
Observable: Class has a free place and waitlist [A]; a staff member tries to book member Z: refused, as for Z booking themselves; A is booked.
Source: implied: C-26; a rule enforced on one route only is no rule.

### C-71: The waitlist adds no rule about a member holding bookings or waitlist entries at overlapping times
Observable: A is booked at the 18:00 yoga class and on the 18:00 spin waitlist; a spin place opens; A is booked into spin unless the existing booking flow refuses overlapping bookings, in which case A is passed over under C-23. A is not removed from the spin waitlist because of the yoga booking.
Source: choice: no new rule that the existing app lacks.

### C-72: Being booked into one class from a waitlist does not remove a member from other waitlists
Observable: A is on waitlists X and Y; A is booked into X; A is still on Y at the same position.
Source: choice: each class stands alone (C-2).

### C-73: Staff-made bookings into a class are not exempt from the class's capacity
Observable: Staff booking a member into a class with 12 of 12 places taken is refused as for a member and the member is not put on the waitlist by staff (C-95); the member may join it themselves.
Source: choice: no staff override exists in the request.

### C-74: The cancellation of a booking returns the same credit or refund whether or not the class has a waitlist
Observable: A member who cancels a booking 24 hours before a class gets the same credit or refund (or none) whether the waitlist for the class is empty or has 4 waiting.
Source: implied: U-6

### C-75: A cancellation is confirmed to the person cancelling without waiting for the waitlist to be processed or for any email to be sent
Observable: With the email provider unreachable, the member cancelling sees their cancellation confirmed; the cancellation is confirmed within the request timeout of the hosting platform (the figure is unconfirmed; commonly 10 to 60 seconds).
Source: implied: runtime rule: a web request has a time limit, and an email send can exceed it.

### C-76: The closing of a waitlist at the class's start time happens without any member or staff member opening the app
Observable: With no one using the app, the entries of a class that started at 18:00 are gone from members' waitlists lists by 18:01.
Source: implied: C-30; it does not depend on someone visiting.

### C-77: The start time is compared as an absolute instant, so daylight saving changes do not shift it
Observable: A class at 18:00 local time on the day clocks change closes its waitlist at 18:00 local time on the clock on the wall that day, not an hour earlier or later.
Source: implied: C-30, C-64

### C-78: Messages that the email provider will not accept at once are held and sent later, not dropped
Observable: A class cancellation with 100 people waiting, with the provider accepting fewer messages a minute than that (the provider's limit is unconfirmed), results in 100 messages delivered eventually, subject to C-67's end at class start.
Source: implied: C-31, C-67

### C-79: The waitlist capacity a staff member can set is a whole number from 0 to 100
Observable: Setting 0 or 100 is accepted; setting 101, -1, 2.5 or an empty value is refused and the previous value is kept. 0 means no one can join (C-47).
Source: choice: a bound is needed; 100 limits the number of messages one class event can cause (C-78).

### C-80: Waitlist entries, positions and history survive a restart or a deployment
Observable: Entries, positions and history before and after a restart of the app are the same; a promotion in progress during a deployment completes (C-65).
Source: implied: C-39

### C-81: If the app cannot send email, staff are told on the waitlist settings, and bookings from the waitlist still happen
Observable: With no email sending set up, the settings show a notice that members will not be emailed; a promotion still books the member and the booking shows in the app.
Source: choice: the waitlist must not run silently without a channel to tell members (C-20); the booking is more important than the message.

### C-82: Waitlist history is kept for 90 days after the class's start time and then deleted
Observable: History for a class that started 91 days ago cannot be found by staff; for a class that started 89 days ago it can.
Source: choice: enough to answer a member's complaint; no longer needed to hold members' details.

### C-83: A member may make at most 30 waitlist join or leave requests in a minute
Observable: The 31st request within a minute is refused with a message to try again shortly and changes nothing.
Source: choice: unbounded join and leave loops would flood history and queue positions; the figure is chosen, not given.

### C-84: After a rollback and a new deployment of the feature, entries still on waitlists at the time of rollback are still there, in the same order
Observable: Waitlist [A, B] at rollback; after the feature returns, the waitlist is [A, B] and a place opening books A.
Source: implied: U-12

### C-85: Waitlist promotion never makes a class's active bookings exceed its capacity
Observable: Capacity 12; through any mix of cancellations, capacity raises and promotions, active bookings never exceed 12 unless staff lowered capacity below the bookings (C-50).
Source: implied: C-1

### C-86: When the first person in line cannot be booked, the next is tried, and so on until someone is booked or no one is left
Observable: Waitlist [A, B, C]; A and B are both without a valid membership; a place opens; A and B are removed and told; C is booked. If C also cannot be booked, the waitlist is empty and the place is open for direct booking.
Source: implied: C-22

### C-87: Waitlist positions are always the whole numbers from 1 to the number waiting, without gaps or repeats
Observable: After any sequence of joins, leaves, promotions, removals and passes-over, staff see positions 1 through n, each once, in order of joining.
Source: implied: C-4, C-5, C-7

### C-88: A member leaves a waitlist for one of eight reasons and no other: they leave it themselves; the class starts; their account is removed; they are booked from it; they are booked by another route; they are removed by staff; they are passed over; the class is cancelled
Observable: Every departure from a waitlist has a record (C-38) naming one of these eight reasons; a departure with no record of one of them does not occur.
Source: implied: "full classes don't turn people away" — a person must never drop off a waitlist for a reason no one can state.

### C-89: A class that is not full looks and works as before for members
Observable: A class with a free place shows no waitlist wording and no join action; booking it is unchanged.
Source: implied: U-6

### C-90: The waitlist never cancels or moves an existing booking
Observable: Booked members' bookings before and after any waitlist action are the same, apart from the place the booked member cancelled or lost.
Source: implied: U-6

### C-91: A member booked from the waitlist receives whatever pre-class reminder other booked members receive
Observable: Where the app sends a reminder to booked members before a class, a member booked from the waitlist receives the same one.
Source: implied: C-17

### C-92: Of the eight departures in C-88, exactly four are messaged to the member: booked from it (C-20), passed over (C-25), removed by staff (C-35), class cancelled (C-31)
Observable: A member who leaves by their own action, whose class has started, whose account is removed, or who is booked by another route receives no waitlist message about that departure.
Source: choice: those four are things done to the member that they would not otherwise know; the other four they did or know.

### C-93: Staff see how many are waiting and the waitlist capacity of a class
Observable: A class with 7 waiting and waitlist capacity 10 shows staff "7" and "10".
Source: implied: U-7, U-9

### C-94: "Staff" means the people who can already edit a class's capacity or cancel a class
Observable: A person who can do either today can use the staff functions of this specification; a person who can do neither cannot.
Source: implied: the request names no new role; the app already distinguishes staff from members (the exact existing roles are unconfirmed).

### C-95: Staff's controls over a waitlist are these four and no others: view it; remove a member from it; turn it on or off; set its capacity
Observable: The staff view offers those four. It offers no way to add a member to a waitlist, reorder a waitlist, clear all entries at once, or turn the feature off for every class at once.
Source: choice: the request asks for no more, and adding a member or reordering would let staff override C-5.

### C-96: A "message" in this specification is an email to the address on the member's account
Observable: The messages of C-20, C-25, C-31, C-32 and C-35 each arrive as an email at the account address, and not by any other channel being required.
Source: choice: the request names no channel; email reaches a member who is not in the app.

### C-97: A member on no waitlist who opens their waitlists list sees that they are on none
Observable: The list shows a statement that the member is on no waitlists, not a blank page or an error.
Source: implied: U-2 at its empty edge.

### C-98: A member who is waiting for a class and tries to book it directly is refused and told they are waiting, with their position
Observable: A member in position 2 who requests to book that class is not booked and is told they are on the waitlist at position 2.
Source: implied: C-26, C-10

### C-99: Staff can set the waitlist capacity of a class
Observable: Setting capacity to 3 on a class with 0 waiting allows 3 entries and refuses the 4th (C-12).
Source: implied: U-9

### C-100: Only staff can change a waitlist's settings or remove a member from it
Observable: A non-staff member's request to remove someone, to turn a waitlist on or off, or to set its capacity is refused and nothing changes.
Source: implied: C-94

### C-101: A waitlist is on for every class by default, including classes that exist when the feature is deployed
Observable: A class that is full on the day of deployment shows a join action to a member who may join (C-3) with no staff action having been taken.
Source: choice: the request asks that full classes not turn people away; making staff switch each class on would leave most classes turning people away.

### C-102: A member who left, was removed by staff, or was passed over may join the same waitlist again, subject to C-3, and goes to the end
Observable: A member removed by staff from position 2 of a waitlist of 4, and who is still allowed to join, is in position 4 after joining again.
Source: choice: as C-15; staff removal does not bar a member from the class.

### C-103: A staff removal of a member who is no longer on the waitlist changes nothing and tells staff so
Observable: Staff on a stale page remove member A, who left a minute earlier: no one else is removed, positions are unchanged, and staff are told A is no longer on the waitlist.
Source: implied: U-8 at its repeated edge.

### C-104: A waitlist with no one on it is shown to staff as empty
Observable: Staff opening a class with 0 waiting see a statement that no one is waiting and the waitlist capacity, not a blank page or an error.
Source: implied: U-7 at its empty edge.
