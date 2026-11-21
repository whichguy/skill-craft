## Use cases

### U-1: A member joins the waitlist of a full class, to hold a place in line instead of being turned away
Flow: The member opens a class occurrence that has no free spots. Where the app used to show only that the class is full, it now shows a control to join the waitlist. The member activates it and sees confirmation that they are on the waitlist, with their position number (the first person in line is position 1).
Source: request

### U-2: A member on a waitlist checks where they stand
Flow: The member opens the class, or their own schedule of bookings, and sees that they are on the waitlist for that class and at which position. They also see a control to leave the waitlist.
Source: implied: a waitlist whose position cannot be seen gives the member no reason to trust it

### U-3: A member on a waitlist is given a spot when one opens, to get into the class
Flow: A booked member cancels (or a spot is otherwise freed). The member at position 1 is booked into the class automatically, receives a notice telling them so, and sees the class among their bookings. Everyone behind them moves up one position.
Source: request

### U-4: A member leaves a waitlist they no longer want to be on
Flow: The member activates the leave control, sees confirmation, and is no longer shown as waitlisted. Members behind them move up one position.
Source: implied: a queue that cannot be left makes people accept classes they cannot attend

### U-5: A member tries to join a waitlist and is refused
Flow: The member tries to join and is told why they cannot (for instance the waitlist is full, they are already booked, the class has ended or is about to start). Nothing about their bookings or any waitlist changes.
Source: implied: every action has refusal cases

### U-6: A member's waitlist place ends without a spot
Flow: The member is on a waitlist, and the class is cancelled, or the waitlist closes before the class, or the member is not eligible when their turn comes, or staff remove them. The member is told that the place has ended and why.
Source: implied: a member who is never told stays home hoping for a class they will not get

### U-7: A member cancels a booking in a class that has a waitlist, so someone else can take the place
Flow: The member cancels through the existing cancel flow. The cancellation completes as it does today. The freed spot goes to the first eligible person in line rather than becoming open to everyone.
Source: implied: the way spots become free

### U-8: Studio staff look at a class's waitlist, to know who is waiting
Flow: Staff open a class occurrence and see its waitlist in order: position, member name and the time each joined. They also see a history of what happened to waitlist entries for that class.
Source: implied: operator's work

### U-9: Studio staff manage a class's waitlist, to control it
Flow: Staff can remove an entry, close or reopen joining for a class, set that class's waitlist size limit, and raise or lower the class's capacity. Raising capacity gives spots to people in line.
Source: implied: operator's work

### U-10: An operator rolls the feature out, pauses it, or goes back to the version before
Flow: The feature starts with every existing class having an empty waitlist and every existing booking untouched. The operator can switch the waitlist off and on. Moving back to a version without a waitlist leaves booking working as it did, and moving forward again picks up sensibly.
Source: implied: operator's work (start, stop, carry on with existing data, go back)

### U-11: Several people act on the same full class at nearly the same moment
Flow: Two members join at once; two booked members cancel at once; the first person in line leaves just as a spot opens; staff remove someone just as they are promoted; a member taps a button twice or retries after a dropped connection. Each person is shown an outcome that is true, and each freed spot goes to exactly one person.
Source: implied: a class everyone wants is where simultaneous actions happen

### U-12: A member's account or a class changes under a waitlist
Flow: A waitlisted member's account is closed, or staff book that member directly, or a class is moved to another time, or the operator switches the feature off while lists exist. The waitlists end up consistent and the people affected are told what they need to know.
Source: implied: state that outlives the action that created it

## Clauses

### C-1: A full class offers the waitlist instead of a dead end
Observable: For a member who could join (C-52), an occurrence that has no free spots shows a control to join the waitlist, in the class listing and in the class detail, where the app previously offered no way to get in. An occurrence with a free spot shows the ordinary book control and no waitlist control.
Source: request

### C-2: Joining puts the member at the end of the line
Observable: After a successful join, the member is behind everyone who was already on that waitlist, and is shown a confirmation that they are on it.
Source: request

### C-3: Joining is not booking and costs nothing
Observable: After joining, the occurrence does not appear among the member's bookings, no credit, payment or fee is taken or held, and the class still shows as full to everyone else.
Source: implied: U-1 (a waitlist place is not a seat)

### C-4: The line is first come, first served
Observable: Of the people on a waitlist, the one whose join the app accepted earliest is the first to be offered a freed spot, then the next earliest, and so on. A member who leaves and joins again goes to the end of the line.
Source: implied: U-1 (a waitlist is a queue)

### C-5: A freed spot is given to the first eligible person in line automatically
Observable: When a spot becomes free on an occurrence while the feature is on (C-29) and the waitlist is open (C-20), the first person in line who is eligible (C-37) is booked into the class with no action on their part. The booking appears in their bookings and the class's booked count rises back by one.
Source: choice: the request says people should not be turned away but not whether the member is booked at once or offered a spot to accept; booking at once leaves no claim window that could run out in a class that is soon, and the member can cancel (C-44)

### C-6: These are the events that free a spot
Observable: A spot counts as freed, and C-5 applies, in exactly these cases: (a) a booking stops being active (C-33): the member cancels it, staff cancel or remove it, or the holder's account is closed or deleted; (b) staff raise the class capacity, one spot for each unit added.
Source: implied: U-3, U-7, U-9

### C-7: A promoted member's booking is an ordinary booking
Observable: Once promoted, the member's entry is gone from the waitlist and the class appears among their bookings exactly as a booking they made directly would, and it can be viewed and cancelled the same way.
Source: implied: U-3

### C-8: A promoted member is told they are booked
Observable: When a member is promoted they receive a notice that states that they are now booked, and names the class and its start date and time in the class's local time with its time zone (C-39).
Source: implied: U-3 (an automatic booking is useless to someone who does not know)

### C-9: Positions close up when someone ahead is gone
Observable: Whenever a person ahead of a member leaves, is promoted, is removed or is skipped, the member's position falls by one. At all times positions on a waitlist are the whole numbers 1 to N with no gaps and no repeats.
Source: implied: U-2, U-3, U-4

### C-10: A member sees their own position
Observable: The confirmation of C-2, the class listing, the class detail, and the member's own schedule each show a waitlisted member as waitlisted for that class together with their current position as a number (the first person in line is 1), and a control to leave (C-11) in place of the join control.
Source: choice: the request does not ask for positions; a member who cannot see where they stand cannot judge whether to wait, and the number costs nothing to show

### C-11: A member can leave a waitlist
Observable: Activating the leave control removes the member's entry, shows confirmation, and the occurrence is no longer shown as waitlisted in the member's schedule.
Source: implied: U-4

### C-12: Leaving a waitlist never touches a booking
Observable: Leaving a waitlist changes no booking of the member, in this class or any other.
Source: implied: U-4

### C-13: A member has at most one entry per class occurrence
Observable: Joining a waitlist the member is already on makes no second entry and does not move them; they are shown their existing position.
Source: implied: U-1 (there is one of a thing)

### C-14: These are the conditions that refuse a join
Observable: A join is refused, with a message naming at least one condition that holds, and changes nothing, when any of these holds: (a) the member is not signed in (they are asked to sign in instead); (b) the member already holds an active booking in the occurrence; (c) the occurrence has a free spot (the message tells them to book instead); (d) the occurrence is cancelled; (e) the occurrence has started or its waitlist has closed (C-20); (f) the member is not eligible to book it (C-37); (g) the waitlist is at its size limit (C-18, C-87); (h) the member is already on the maximum number of waitlists (C-19); (i) joining has been closed for the occurrence by staff (C-26); (j) the waitlist feature is switched off (C-29); (k) the member has reached the hourly join limit (C-75); (l) the occurrence has no capacity limit (C-34).
Source: implied: U-5

### C-15: Spots are never given out of turn
Observable: While the feature is on and anyone is on an occurrence's waitlist, a freed spot is never taken by a person who is not first in line (apart from people skipped for ineligibility, C-17); a direct attempt to book it by someone else is refused as full.
Source: implied: U-7

### C-16: The waitlist can run out
Observable: When a spot is freed and nobody on the waitlist is eligible (or the waitlist is empty), the spot becomes an ordinary free spot that anyone may book under the usual rules.
Source: implied: U-3

### C-17: A member is skipped at promotion if they cannot be booked
Observable: At the moment of their turn, a member is skipped (their entry is removed, they get the notice in C-22 naming the condition, and the next in line is considered) when either of these holds: (a) their account is suspended, closed or deleted; (b) they are not eligible (C-37), for example no membership, no credits, a failed payment (C-38) or an unmet class restriction.
Source: implied: U-6

### C-18: A waitlist has a default size limit of 20
Observable: Unless staff set a different limit (C-87), an occurrence's waitlist holds at most 20 members; the 21st person trying to join is refused (C-14 g).
Source: choice: the request gives no number; a limit stops an unbounded queue of people who will never get in, and 20 is a round figure for studio-sized classes

### C-19: A member can be on at most 10 waitlists at once
Observable: A member already on 10 waitlists who tries to join an 11th is refused (C-14 h). Leaving, being promoted or having an entry end makes room.
Source: choice: stops one member from queueing for everything; 10 is a round figure

### C-20: A waitlist is open until 60 minutes before the class starts
Observable: An occurrence's waitlist is open exactly while the app's clock is earlier than 60 minutes (3,600 seconds of real time, also on a night when the clocks change) before the occurrence's start time, and the occurrence is not cancelled. When it is not open no one can join and no one is promoted. Within 60 seconds after it closes (C-70), every remaining entry is removed and each member receives the notice in C-22 saying the waitlist ended without a spot.
Source: choice: promoting someone later than this would book them into a class they cannot realistically get to; 60 minutes is a round figure

### C-21: A spot freed while the waitlist is closed is an ordinary free spot
Observable: A spot freed when the waitlist is closed (C-20) is not promoted to anyone; the class shows it as a free spot and anyone may book it under the usual booking rules.
Source: choice: follows from C-20

### C-22: A member whose place ends is told why
Observable: When an entry ends other than by the member leaving, being promoted (C-5), account closure (C-61) or being booked by other means (C-62), the member receives a notice containing: the class name, the class's start date and time in its local time, and exactly one reason from this list: the class was cancelled; the waitlist closed before a spot opened; they were not eligible when their turn came (naming which condition of C-17 applied); staff removed them.
Source: implied: U-6

### C-23: A cancelled class ends its waitlist
Observable: When staff cancel an occurrence, all its waitlist entries are removed and each member receives the notice in C-22. Nobody is promoted.
Source: implied: U-6

### C-24: Staff can see a class's waitlist
Observable: A staff member opening an occurrence sees its waitlist ordered by position, with each entry's position, member name and the date and time they joined; an empty waitlist is shown as empty.
Source: implied: U-8

### C-25: Staff can remove someone from a waitlist
Observable: A staff member removing an entry makes it disappear from the list, and the removed member receives the notice in C-22.
Source: implied: U-9

### C-26: Staff can close and reopen joining for a class
Observable: For each occurrence staff can mark joining closed or open (default open). Closing joining stops new joins only; people already on the list stay and are still promoted.
Source: implied: U-9

### C-27: Raising capacity promotes people in line
Observable: When staff raise an occurrence's capacity by k, up to k people are promoted, in order, while there are eligible people in line, the feature is on and the waitlist is open; the rest of the new spots are ordinary free spots.
Source: implied: U-9

### C-28: Lowering capacity never removes bookings
Observable: When staff lower capacity to or below the number of active bookings, no booking is cancelled, the class shows as full, and nobody is promoted until the active bookings fall below the capacity.
Source: implied: U-9

### C-29: The operator can switch the waitlist off
Observable: With the waitlist switched off: no member is shown a join control, every join is refused (C-14 j), no promotion happens, and existing entries are kept (except as C-20 ends them).
Source: implied: U-10

### C-30: Members never see who else is waiting
Observable: A member never sees another member's name or any identifying detail of anyone on a waitlist, nor of who was promoted or skipped. Only staff see names (C-24).
Source: implied: privacy

### C-31: Existing data carries on
Observable: When the feature first goes live, every occurrence has an empty waitlist and no booking is changed, added or removed.
Source: implied: U-10

### C-32: Going back to the version before leaves booking working
Observable: If the app is reverted to a version without the waitlist, bookings, cancellations and full-class behaviour work as they did before the feature; no booking is lost or changed by the revert.
Source: implied: U-10

### C-33: "Full" means active bookings have reached capacity
Observable: An occurrence is full when its number of active bookings is equal to or greater than its capacity. An active booking is one of: booked by the member directly; booked through promotion from the waitlist; added by staff; already checked in; or in any other state the app already has in which the booking takes up a spot today. A booking cancelled by the member, cancelled by staff or removed because its account was closed is not active. An occurrence with capacity 10 and 10 active bookings shows as full; cancelling one of them makes it not full. An occurrence that is not full has a free spot.
Source: implied: request sentence "full classes" (what makes a class full must be fixed)

### C-34: A class with no capacity limit never has a waitlist
Observable: An occurrence that the app allows to be booked without a capacity limit is never full and shows no waitlist controls, and staff are not offered waitlist settings for it.
Source: implied: "full classes" (something that is never full cannot be waitlisted)

### C-35: A waitlist entry is for exactly one spot
Observable: One entry is one member wanting one spot. Where the app lets a member book more than one spot in an occurrence (for example for a guest), a promotion gives them one spot only.
Source: choice: the request does not say how many spots a person can queue for; one keeps the line simple and fair

### C-36: A waitlist entry belongs to one occurrence only
Observable: In this specification an "occurrence" is one class on one date at one start time. Joining the waitlist for one occurrence puts the member on no waitlist for the same class on any other date or for any series it belongs to; each date has its own waitlist and its own positions.
Source: implied: "full classes" (a class that happens repeatedly fills one date at a time)

### C-37: "Eligible" means the app's existing booking rules, apart from fullness
Observable: A member is eligible for an occurrence when the app's existing rules would let them book it directly if it had a free spot. The fact that it has no free spot does not by itself make a member ineligible. Joining and promotion both use this one test.
Source: implied: C-14 f and C-17 b (the word "eligible" must name one test)

### C-38: Promotion charges what a direct booking would charge, at the moment of promotion
Observable: If booking the class directly takes a credit, payment or fee from the member, promotion takes the same amount at the moment of promotion (not at joining), and the member's account shows that charge. If it cannot be taken, the member is skipped under C-17 b and no booking exists.
Source: implied: C-3 and U-3 (a promoted booking is an ordinary booking, so it costs what one costs)

### C-39: Times are shown in the class's local time zone
Observable: Every class date and time shown on a waitlist screen or in a waitlist notice is in the local time zone of the place where the class is held, with the time zone named.
Source: implied: C-8 and C-20 (a time with no zone is ambiguous)

### C-40: Notices go through the channels the app already uses
Observable: Every notice this feature sends (C-8, C-22, C-50) goes through every channel the app already uses to confirm bookings that the member can receive on (a phone alert is skipped for a member who has turned phone alerts off or has no device). If the app uses no channel, or the member can receive on none, it goes by email to the address on the member's account.
Source: choice: the request names no channel; reusing the channels members already receive keeps them from missing it

### C-41: Notices are sent even to members who have opted out of marketing
Observable: A member who has turned off promotional or marketing messages still receives the notices of C-8, C-22 and C-50.
Source: choice: these notices change what the member is committed to or expecting, so they are not promotional

### C-42: A failed notice never undoes a promotion
Observable: If a promoted member's notice cannot be delivered, they still hold the booking and see it in their bookings (C-7).
Source: implied: C-8 (the booking is the fact; the notice only reports it)

### C-43: Notices arrive within 5 minutes under normal conditions
Observable: A notice is handed to its channel within 5 minutes of the promotion or the ending of the entry it reports.
Source: choice: the request gives no time; a member needs to hear in time to act, and 5 minutes is a round figure (the figure for what the sending service itself takes to deliver is unconfirmed)

### C-44: A promoted booking can be cancelled without penalty for 2 hours
Observable: If the app charges a late-cancellation fee, forfeits a credit or applies any penalty for cancelling close to the start, then a member who cancels a booking they received by promotion within 2 hours after being promoted pays none of it, even if the class is inside the app's normal late-cancellation period. After the 2 hours the app's normal rules apply.
Source: choice: a member booked automatically did not choose the timing, so penalising an immediate cancellation would turn the feature against them; 2 hours is a round figure

### C-45: Staff can see what happened to each waitlist entry
Observable: Staff opening an occurrence can see a history of its waitlist events, each with the time, the member's name and exactly one event type from: joined; left; promoted; skipped (with the C-17 condition); removed by staff (with the staff member's name); ended because the class was cancelled; ended because the waitlist closed; ended because the account was closed; ended because the member was booked by other means; notice failed to send.
Source: implied: U-8 (staff need to answer "what happened to this member's place")

### C-46: Waitlist history is kept 90 days after the class
Observable: The history of C-45 for an occurrence remains visible to staff for 90 days after the occurrence's start time, and is then deleted.
Source: choice: a waitlist record must not live forever, and 90 days covers disputes about a missed class

### C-47: "Staff" means whoever the app already lets manage class bookings
Observable: The staff actions in this feature (view the waitlist and its history, remove an entry, close or reopen joining, set the limit) are available to exactly the accounts that can already see who is booked in a class and cancel their bookings, and to no other account.
Source: implied: U-8, U-9 (the request mentions no new role)

### C-48: The waitlist size limit must be a whole number from 0 to 100
Observable: Staff entering a size limit that is not a whole number from 0 to 100 (empty, negative, fractional, text, or above 100) are refused with a message and the limit stays as it was. A limit of 0 means no one can join.
Source: choice: a bound with a value is needed; 100 is far above studio class sizes

### C-49: Moving a class's start time moves its waitlist window
Observable: When staff change an occurrence's start time, the closing time of C-20 is measured from the new start time. Existing entries are kept unless the new start time is less than or equal to 60 minutes from now, in which case they end at once under C-20. If the class is moved later so that the closing time is again in the future, the waitlist is open again (and empty).
Source: implied: C-20 (the closing is defined relative to the start)

### C-50: Waitlisted members are told when the start time changes
Observable: When an occurrence's start time changes, each member on its waitlist receives the same notice that booked members of the occurrence receive; if the app sends no such notice, a notice containing the class name, the old start date and time and the new start date and time.
Source: choice: a member waiting for a class at a time they no longer have should find out; reuses the booked members' notice where it exists

### C-51: Leaving a waitlist is always possible while the entry exists
Observable: A member can leave a waitlist they are on whatever the state of the class or the feature: even when joining has been closed by staff, the waitlist feature is switched off, the limit has been lowered, or the member has reached the hourly join limit.
Source: implied: U-4 (the member should never be stuck on a list)

### C-52: The join control is shown only when joining would work
Observable: On a full occurrence, the join control appears only when a join made at that moment would succeed (none of the refusals in C-14 would apply to this member). Otherwise the occurrence shows as full and offers no join control; the exact wording is not fixed.
Source: implied: C-1 and C-14 (a control that can only refuse is another way of turning people away)

### C-53: Two joins at the same moment get different positions in the order the app accepted them
Observable: When two members join the same waitlist at the same moment, both are placed (limit permitting), no two entries share a position, and the one the app accepted first is ahead. If only one place is left under the size limit, exactly one join succeeds and the other is refused under C-14 g.
Source: implied: U-11

### C-54: Two cancellations at the same moment free two spots and promote two people
Observable: When two booked members cancel from the same full occurrence at the same moment, the people at positions 1 and 2 (if both eligible) are promoted, each into one spot; no spot is given to two people and none is left free while eligible people are waiting.
Source: implied: U-11

### C-55: The same cancellation received twice frees one spot
Observable: If one cancel of one booking is received twice (a double tap, a retry), the booking is cancelled once, at most one person is promoted, and the second request is told the booking is already cancelled.
Source: implied: U-11

### C-56: Leaving twice is harmless
Observable: Leaving a waitlist the member is no longer on is answered with a statement that they are not on it; nothing else changes and no error suggests a failure.
Source: implied: U-11

### C-57: A free spot and the person promoted into it are never seen apart
Observable: While the feature is on, an occurrence's waitlist is open (C-20) and has an eligible person on it, no one looking at the occurrence at any moment sees a free spot; the booked count either still stands at capacity or already includes the promoted member.
Source: implied: C-15 (if it were visible, a direct booking could slip in)

### C-58: A first-in-line member who leaves just as a spot opens never costs the spot
Observable: If the member at position 1 leaves at the same moment a spot is freed, one of two outcomes holds. Either the leave is accepted first, so the member is confirmed as having left and the next eligible person is promoted. Or the promotion is accepted first, so the member is told they are now booked and the booking stays (C-12). In both cases the freed spot goes to exactly one person.
Source: implied: U-11

### C-59: Staff removing an entry that has just been promoted does not cancel the booking
Observable: If staff remove an entry at the moment the member is promoted, either the member is removed with the C-22 notice and the next person is promoted, or staff are told the member is no longer on the waitlist because they are booked and the booking stays.
Source: implied: U-11

### C-60: A cancelled class sends no "you are booked" notice
Observable: No member is sent the C-8 notice for an occurrence after it has been cancelled; where a cancellation and a promotion meet, after both complete the member holds no booking for the occurrence.
Source: implied: U-12

### C-61: Closing an account removes its waitlist entries
Observable: When a member's account is closed or deleted, every waitlist entry of theirs is removed within 60 seconds (C-70) without a notice, and members behind them move up one place on each list.
Source: implied: U-12

### C-62: Being booked by other means ends the member's entry for that occurrence
Observable: If a member on an occurrence's waitlist comes to hold an active booking in it by any other means (for example staff add them directly), their entry for that occurrence is removed and no C-22 notice is sent.
Source: implied: U-12 (a member cannot be both booked and waiting)

### C-63: Entries for different classes are independent
Observable: Being promoted into one occurrence, or leaving one waitlist, changes no other waitlist entry the member has, including entries for other occurrences at overlapping times.
Source: choice: the request is silent; the member decides which spot to keep, and C-37 already refuses a promotion the app's rules would refuse

### C-64: Closing time is a rule about time and applies even when the feature is switched off
Observable: Entries still end at the closing time of C-20 while the waitlist feature is switched off; the notices of C-22 are still sent.
Source: implied: U-12

### C-65: While the feature is off, members still see their own entries
Observable: While the feature is switched off, a member who is on a waitlist still sees that entry with its position and the leave control (C-51), together with an indication that waitlist promotion is paused.
Source: implied: U-12 (hiding an entry would make the member think it is gone)

### C-66: Staff removing someone who is not on the list is told so
Observable: A staff removal of an entry that no longer exists is answered with a statement that the member is not on the waitlist; nothing else changes.
Source: implied: U-11

### C-67: Every action is decided on the current state, not on what the page showed
Observable: The runtime is a hosted service used from browsers and phones, where a page can be minutes old, a tab can be left open, and the same person can act from two devices. An action taken from a stale page (a join from a page that still shows the class as full when a spot has since opened; a leave from a page that still shows the member waitlisted after they were promoted) is judged against the state at the moment it arrives, and the member is shown the true result and the true current state.
Source: implied: Pass 4 (pages are stale by nature of the platform)

### C-68: The app's own clock decides every time rule
Observable: The 60-minute closing (C-20), the 2-hour penalty-free window (C-44) and the 90-day history (C-46) are measured by the app's server clock, not the clock of the member's or staff member's device: a member whose phone clock is two hours wrong is accepted or refused exactly as a member whose clock is right.
Source: implied: Pass 4 (device clocks cannot be trusted)

### C-69: A notice that cannot be delivered is retried and then recorded
Observable: The services that deliver email and phone alerts impose sending-rate limits and can reject or delay messages (their exact figures are unconfirmed). Forced by this, a notice that fails to deliver is retried until it is delivered, or until the class starts, or for 24 hours, whichever comes first; if it is still undelivered then, the staff history shows "notice failed to send" for that member and occurrence (C-45). No notice is silently dropped.
Source: choice: 24 hours is a round figure for how long a retry is worthwhile; the provider limits are unconfirmed

### C-70: A bulk change completes all its promotions within 60 seconds
Observable: When one event gives out many spots at once (staff raise a capacity by up to 100) or ends many entries at once (a class with up to 100 waiting is cancelled), every promotion and every entry removal it causes is complete within 60 seconds, in line order; until a promotion completes its spot cannot be booked by anyone else (C-57). The 60-second figure is unconfirmed against the real infrastructure.
Source: choice: a hosted service limits how long one request may run, so large changes must not depend on one request lasting; 60 seconds is a round figure

### C-71: Production notices come from an authenticated sender
Observable: Before the feature is used outside a development environment, the emails it sends come from a sender address whose domain is authenticated in the way mail providers require (SPF and DKIM pass when the message headers are inspected), so that notices reach the inbox and not a spam folder.
Source: implied: Pass 4 (mail providers reject or hide unauthenticated mail)

### C-72: Waitlist actions only travel over encrypted connections
Observable: A member or staff request that tries to join, leave or manage a waitlist over an unencrypted connection is refused or redirected to the encrypted address, and changes nothing.
Source: implied: Pass 4 (a production service carries sign-in credentials)

### C-73: When an account is deleted its name leaves the waitlist history
Observable: After a member's account is deleted, the staff history of C-45 for each occurrence still shows the event but no longer shows the member's name or contact detail (it shows that the member was removed).
Source: implied: Pass 4 (people can ask for their data to be erased; C-46 would otherwise keep it)

### C-74: Waitlist controls work without a mouse or sight
Observable: The join and leave controls, the confirmations, the refusals and the position number can be reached and operated using only a keyboard, and are announced by a screen reader as text (the position is not conveyed only by colour or position on screen).
Source: choice: the request names no accessibility standard; this is the least that keeps members using assistive technology from being turned away

### C-75: A member can make at most 30 join requests per hour
Observable: When the app has received 30 join requests from a member in the last 60 minutes, whatever their results (those refused under this clause not counted), the next is refused with a message saying so and changes nothing, until fewer than 30 fall in the last 60 minutes. Leaving is never limited (C-51).
Source: choice: stops a member (or a script) from flooding the line, the staff history and the notices; 30 is a round figure well above honest use

### C-76: Booking a class with a free spot is unchanged
Observable: For an occurrence with a free spot (and no one waiting), booking works exactly as before the feature: the same steps, the same checks, the same confirmation.
Source: implied: Pass 5 (existing behaviour that must hold)

### C-77: Cancelling a booking where no one is waiting is unchanged
Observable: Cancelling a booking for an occurrence with an empty waitlist behaves exactly as before the feature: the same checks, fees or refunds, and confirmation; the spot becomes an ordinary free spot.
Source: implied: Pass 5

### C-78: Existing cancellation rules apply to every booking
Observable: The app's existing cancellation rules (deadlines, fees, credit refunds) apply unchanged to bookings that came from the waitlist, except for the 2-hour penalty-free window of C-44.
Source: implied: Pass 5 (C-7: a promoted booking is ordinary)

### C-79: A promotion never takes bookings above capacity
Observable: After any promotion, an occurrence's active bookings are at most its capacity. (Staff lowering capacity below the bookings, C-28, is the only way they can exceed it.)
Source: implied: Pass 5 (no overbooking)

### C-80: One freed spot gives one promotion, and an entry is promoted once
Observable: Each freed spot results in at most one promotion; and a given entry is promoted at most once, so a member never holds two bookings for one occurrence from one waitlist entry.
Source: implied: Pass 5 (nothing done twice that should happen once)

### C-81: The same rules hold on every path into the app
Observable: Whatever way a member or staff member reaches the waitlist (the website, a phone app, a staff screen, any interface other programs use), the same refusals of C-14, the same limits of C-18, C-19, C-20 and C-75, and the same results apply; a refusal on one path is a refusal on all.
Source: implied: Pass 5 (a rule enforced in one path and not another)

### C-82: Members act only on their own entries and only staff manage lists
Observable: A member's attempt to leave someone else's entry, to view another member's position, or to use a staff action (C-24, C-25, C-26, C-45, C-87) is refused and changes nothing.
Source: implied: Pass 5 (someone seeing or doing what they may not)

### C-83: A promotion happens completely or not at all
Observable: A promotion either does everything (booking exists, the charge of C-38 is taken, the entry is gone, the notice is queued) or nothing; there is never a moment at which a member is both booked and still on the waitlist for the same occurrence, or charged without a booking, or booked without having been charged.
Source: implied: Pass 5 (partial completion)

### C-84: A fault in the app never costs a member their turn
Observable: If a promotion fails for a reason that is not the member's eligibility (an outage, an error in the app), the member keeps their entry and place, the spot is not given to anyone behind them, and the promotion is tried again until it succeeds or the waitlist closes (C-20).
Source: implied: Pass 5 (data lost on the way; C-17 is the only legitimate reason to skip)

### C-85: A notice contains nothing about other members
Observable: No notice and no member-facing screen of this feature contains the name, contact detail or position of any other member (C-30).
Source: implied: Pass 5 (someone seeing what they may not)

### C-86: Each event produces one notice per member
Observable: A given promotion, ending, removal or start-time change produces one notice per affected member; a retry (C-69), a repeated request (C-55, C-56) or a bulk change (C-70) never produces a second notice for the same event.
Source: implied: Pass 5 (a thing done twice that should happen once)

### C-87: Staff can set a class's waitlist size limit
Observable: For each occurrence staff can set the waitlist size limit (default 20, C-18; accepted values C-48). Lowering the limit below the current length removes nobody and stops new joins until the length drops below the limit.
Source: implied: U-9

### C-88: While the feature is off, freed spots are ordinary free spots
Observable: While the waitlist feature is switched off, a spot that becomes free is shown as a free spot that anyone may book under the usual rules, even if entries are still on the waitlist.
Source: choice: holding spots for a line that cannot be promoted would leave classes empty for as long as the feature is off, which is exactly when the operator wants plain booking back

### C-89: Switching the feature on again resumes promotions
Observable: When the waitlist feature is switched on, every occurrence that has a free spot, an open waitlist (C-20) and eligible people in line is promoted in order, completing within the time of C-70.
Source: implied: U-10

### C-90: Going forward again after a revert treats old entries like an off period
Observable: If the waitlist is reintroduced after a revert (C-32), entries that were left from before are handled as if the feature had been switched off meanwhile: C-64 and C-65 apply, and C-89 applies when the feature is on.
Source: implied: U-10 (data outlives the version that wrote it)

### C-91: The same information is shown in the app
Observable: Whenever a notice of C-8, C-22 or C-50 is sent, the member also sees the same information in the app (in their bookings, their waitlist entries or their notices) the next time they open it.
Source: choice: a notice on a channel can be missed or fail (C-42), so the app itself must still tell the member

### C-92: A promotion notice also gives the location and how to cancel
Observable: The notice of C-8 also contains the class's location where the app records one, and a way to cancel the booking (a link or instruction).
Source: choice: the request names nothing about content; a member who now has to attend needs to know where and how to back out

### C-93: In-app notice information stays for 30 days
Observable: The information of C-91 remains visible to the member in the app for 30 days after the event it reports, and is then removed.
Source: choice: information shown to a member must not accumulate forever; 30 days is a round figure that outlasts any class a member could be waiting for
