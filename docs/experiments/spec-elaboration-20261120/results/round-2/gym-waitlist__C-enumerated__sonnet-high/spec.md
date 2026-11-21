## Use cases

### U-1: A signed-in member joins the waitlist of a full class, to be booked if a seat opens
Flow: The member opens a class that is full. Instead of a dead end they see that the class is full and a control to join the waitlist. They select it, are shown what joining means (no seat is held; if a seat opens they are booked automatically on the same terms as a normal booking; they can leave at any time), and confirm. They then see that they are on the waitlist and their position (1 = next in line).
Source: request

### U-2: A waitlisted member is booked automatically when a seat opens
Flow: A seat in the class becomes free. The member at the front of the waitlist (among those still able to book) is given the seat without doing anything. They receive a message saying they are now booked, with the class details. The class appears in their bookings as a normal booking and no longer as a waitlist entry.
Source: request ("so full classes don't turn people away")

### U-3: A waitlisted member checks where they stand
Flow: The member opens their own bookings area and sees every class they are waitlisted for, each with class name, start date and time, and current position.
Source: implied: a person who joins a queue needs to see that they are in it and how far it has moved

### U-4: A waitlisted member leaves the waitlist
Flow: The member selects "leave waitlist" on a class they are waitlisted for and confirms. They see that they are no longer on it. Members behind them each move up one place.
Source: implied: a queue that can be joined can be left; plans change

### U-5: A member is refused when trying to join a waitlist
Flow: The member attempts to join and is told, in words naming the specific reason, why they cannot, and what (if anything) they can do instead. No waitlist entry is created. The reasons are: they already hold a booking in the class; they are already on its waitlist; the class has free seats; the waitlist is at its limit; they cannot book that class for a reason that would also stop a normal booking; the class has passed its booking close or is cancelled; the waitlist is turned off for that class.
Source: implied: every action that can be refused needs a stated refusal (unhappy path of U-1)

### U-6: A waitlisted member is told when their place ends without a seat
Flow: The class starts or booking closes while the member is still waitlisted, or the class is cancelled, or the waitlist is switched off, or the member is passed over because they can no longer book it, or staff removed them. The member receives a message saying their waitlist place has ended and why, and the class disappears from their waitlist entries.
Source: implied: a queue that ends silently leaves the person waiting for something that will never happen

### U-7: A booked member cancels, and the seat passes to the waitlist
Flow: A member with a booking in a full class that has a waitlist cancels it using the normal cancel action. They see their normal cancellation result. The seat goes to the front of the waitlist, not back to whoever asks first.
Source: implied: cancellation is the commonest way a seat opens

### U-8: A visitor who is not signed in sees a full class
Flow: The visitor sees the class is full. If they try to join the waitlist they are taken to sign in, and after signing in they return to that class and can join.
Source: implied: a waitlist entry belongs to a member

### U-9: A staff member looks at who is waitlisted for a class
Flow: Staff open a class and see its waitlist in order: position, member name, when they joined, and whether the member can currently book the class (and if not, why).
Source: implied: whoever runs the classes needs to see the queue they are running

### U-10: A staff member adds a member to a waitlist or removes one from it
Flow: Staff choose a member and a class and either add them (at the end, or at a position they type) or remove an existing entry. They see the resulting waitlist. The member receives a message about it.
Source: implied: a member who phones the front desk, or an entry that is wrong, has to be fixable by staff

### U-11: A staff member undoes a promotion made in error
Flow: Staff cancel the promoted booking using the existing cancel action with the "error" option (C-66), see that the member's credit or charge has been returned and that the seat has gone to the next member in line, and, if the member who lost it should be next in line again, add them back at position 1 (C-48).
Source: implied: "undo something it did by mistake"

### U-12: An operator turns the waitlist on for the first time and checks that it works
Flow: After the feature has been released, the operator opens the waitlist settings, sees it is Off, turns it On, and sees it is On. They open a full class and see the join control. They see the status view (C-61) show the feature running.
Source: implied: someone has to turn it on and know it worked

### U-13: An operator changes the limit, or turns the waitlist off for one class or for everyone
Flow: The operator opens the settings, changes the number of places on a waitlist, switches one class's waitlist off, or switches the whole feature off. They see the new setting, and members affected receive the message in C-31.
Source: implied: "configure it", "turn it off, for everyone or for one case"

### U-14: An operator watches the waitlist and finds the one thing that went wrong
Flow: The operator opens the status view for counts, then the event log, filters it to failures (for example messages that could not be delivered), and finds the member, the class and the reason.
Source: implied: "watch it while it runs, and find the one thing that went wrong among the many that went right"

### U-15: An operator releases the feature onto an app that already has classes, bookings and members, and can go back
Flow: The feature is released with existing bookings and full classes in place; nothing changes for anyone until it is turned on; later, to go back to the release before, the operator turns the waitlist off everywhere and rolls back, and every booking is still intact.
Source: implied: "carry on with the data that already exists", "go back to the version before"

## Clauses

### C-1: A waitlist belongs to one class occurrence (one class at one date and time), and a class occurrence has at most one waitlist
Observable: Waitlisting for Monday 18:00 Yoga does not place the member on the waitlist for Wednesday 18:00 Yoga, and a member's position is counted only among entries for that same occurrence.
Source: implied: "full classes" are full per scheduled session

### C-2: A class occurrence is full when the number of bookings holding a seat equals its capacity
Observable: A class with capacity 12 and 12 bookings is shown as full; with 11 bookings it is not shown as full.
Source: implied: "full classes"

### C-3: A full class that has an open waitlist shows a join-waitlist control in place of the book control; a waitlist is open when it is On globally and for that class, the class is not cancelled, booking has not closed, and the entries are fewer than the limit
Observable: A signed-in member opening a full class sees that it is full and a control to join the waitlist, and no control that books them straight in. If the waitlist holds as many entries as the limit, they instead see that the waitlist is full and no join control. If the waitlist is not open for any other reason they see the class as full with no join control.
Source: request

### C-4: Before the join is created the member is shown the terms of joining, and the join is created only when they confirm
Observable: The member sees, before confirming, three statements: no seat is held, they will be booked automatically on the same terms as a normal booking (including any credit used or charge made) if a seat opens, and they can leave at any time. Cancelling out of the confirmation creates no entry.
Source: choice: automatic booking can spend a credit or charge money, so the member must have agreed to it first

### C-5: A confirmed join puts the member at the end of the class's waitlist
Observable: With 3 entries already present, a new member joins and is shown position 4 immediately.
Source: request

### C-6: Waitlist order is the order in which joins were confirmed, earliest first, and no two entries share a position
Observable: Members who joined at 09:00, 09:05 and 09:10 are positions 1, 2 and 3 respectively; two joins that arrive at the same instant still get two different positions.
Source: implied: a waitlist is first come, first served

### C-7: A waitlist entry holds no seat and does not count toward capacity
Observable: A class with capacity 12, 12 bookings and 5 waitlist entries still shows 12 of 12 booked; the instructor's roster of attendees lists only the 12 booked members.
Source: implied: a waitlisted member is not attending

### C-8: When a seat in a class becomes free and that class's waitlist has entries, the first entry whose member can book the class is booked into the seat
Observable: Seat freed, waitlist A (1), B (2), C (3), all able to book: A holds a booking in the class, B becomes position 1, C becomes position 2.
Source: request

### C-9: The seat is offered to the waitlist only; a free seat is never taken by anyone not on the waitlist while any waitlisted member can still book the class
Observable: While the waitlist has an entry able to book, a different member who attempts to book directly at the moment the seat frees is told the class is full (C-77), and the seat ends up with the waitlist's first member, however the two requests were ordered in time.
Source: implied: queue-jumping defeats the point of a queue

### C-10: A booking made by promotion is an ordinary booking
Observable: In the promoted member's bookings it looks the same as a booking made directly, can be cancelled with the same cancel action, and is subject to the same cancellation rules (including any late-cancellation rule) as a direct booking. The app does not add exemptions or penalties because it came from the waitlist.
Source: choice: the loosest rule that keeps existing behaviour unchanged

### C-11: A promoted booking uses the same credit or charge a direct booking of that class would use, taken at the moment of promotion
Observable: A member on a 10-class pack with 4 left is promoted and then has 3 left; a member on unlimited membership is promoted and nothing is deducted. Joining the waitlist itself costs nothing.
Source: choice: this is the only reading consistent with C-4 and with not changing existing pricing

### C-12: "Can book the class" for the waitlist means the member would pass every rule the app applies to a direct booking of that class, other than the class being full
Observable: The rules are, at least: the member account is active and not suspended or blocked; their membership or plan is valid on the class date; they have a remaining credit or allowance if their plan limits classes, or, if the class is paid per booking, a payment that can be taken; they do not already hold a booking in this class; they hold no booking overlapping this class in time if the app forbids overlapping bookings; the class is not cancelled; and booking had not closed at the moment the seat freed (a promotion in progress when the close arrives still completes, C-79). Any other rule the app already enforces on direct booking is part of this list. Which of these the app enforces today is unconfirmed; this spec adds no rule of its own.
Source: implied: promotion must not create a booking the member could not have made themselves

### C-13: A waitlisted member who can no longer book the class when their turn comes is passed over, removed from the waitlist, and the next entry is considered
Observable: A at position 1 has used their last credit, B is at position 2 and eligible: B gets the seat, A is no longer on the waitlist and A's own bookings are unchanged.
Source: choice: the alternative, keeping A in front of B, leaves a seat that cannot be filled while a willing member waits

### C-14: A member passed over under C-13 is sent a message that states the reason, from the list in C-12
Observable: A receives a message such as "you were passed over because you have no class credits remaining", naming the specific reason.
Source: implied: U-6

### C-15: A member's waitlist entries are listed in their own bookings area with class name, start date and time, and current position, and not mixed in with bookings
Observable: A class the member is waitlisted for appears in a separate "waitlist" list showing "position 3" (or equivalent); it does not appear in the list of confirmed bookings.
Source: implied: U-3

### C-16: Position shown to a member is correct as of the moment the page or screen is loaded or refreshed
Observable: After the member ahead leaves, the next load shows the position reduced by one.
Source: choice: no live push of position changes is required; correct-on-load is the loosest that serves

### C-17: A member sees only their own position and entries, never who else is on a waitlist and never the length of the waitlist beyond being told whether it is full
Observable: No screen available to a member shows another member's name or the total number of entries; they can see "waitlist full" when the limit is reached.
Source: implied: privacy of other members

### C-18: Leaving the waitlist removes the entry and moves every entry behind it up by one
Observable: C at position 3 leaves: D, previously 4, is now 3. The leaver sees that they are not on the waitlist.
Source: implied: U-4

### C-19: Joining is refused if the member already holds a booking in the class
Observable: The member sees a message that they are already booked in this class; no entry is created.
Source: implied: U-5

### C-20: Joining when the member is already on the waitlist creates no second entry and shows their existing position
Observable: Repeating the join (double click, retry, two tabs) leaves exactly one entry and the same position shown.
Source: implied: U-5 and repeat requests

### C-21: Joining is refused if the class has a free seat, and the member is told the class has space and is shown the normal booking route
Observable: No entry is created; the message says there are places left.
Source: implied: U-5; choice: the join is not silently turned into a booking because a booking can spend credit

### C-22: Joining is refused if the waitlist already holds the maximum number of entries
Observable: The member is told the waitlist for the class is full; no entry is created; the join control is not shown on later views until a place opens.
Source: implied: unbounded queues serve nobody; the limit's value is in C-35

### C-23: Joining is refused if a reason that concerns the member (account state, plan validity, credit or payment, overlapping booking, from C-12) would stop them booking the class, and the refusal names that reason
Observable: A suspended member, or one with no credits, sees the specific reason and no entry is created.
Source: implied: U-5

### C-24: Joining is refused if the class is cancelled or its booking has closed
Observable: The member is told the class is no longer open for booking; no entry is created.
Source: implied: U-5

### C-25: Booking close for the waitlist is the same moment after which the app today refuses direct bookings of that class; where the app has no such moment, it is the class's start time
Observable: If direct bookings stop 30 minutes before start, joins also stop 30 minutes before start, and seats freed from then on are not offered to the waitlist (C-91); if direct bookings never stop earlier, the same happens at the start time.
Source: choice: the request gives no deadline; reusing the existing one avoids two competing deadlines

### C-26: Joining is refused if the waitlist is switched off for the class
Observable: A join request made for a full class whose waitlist is off (for example from a page loaded before it was switched off) creates no entry and tells the member the waitlist is not available for the class.
Source: implied: U-5; the switch is in C-57

### C-27: A member who is not signed in who tries to join is taken to sign in, creates no entry, and returns to the class after signing in
Observable: After signing in, the member lands on the same class and can join.
Source: implied: U-8

### C-28: A member who cancels their own booking does not get the seat back ahead of the waitlist
Observable: Full class with waitlist A, B; member M cancels; A is booked, not M. If M then wants back in, M may join the waitlist and is placed at the end.
Source: implied: U-7, C-9

### C-29: When booking closes with entries still on the waitlist, every remaining entry is removed
Observable: Within 5 minutes after the booking-close moment (C-92) the waitlist of that class is empty; from the moment itself no member is promoted into it (C-91) for a seat freed after that moment.
Source: implied: a queue past its deadline can never be served

### C-30: When a class is cancelled, its whole waitlist is removed
Observable: Within 5 minutes (C-92) no waitlist entries remain for the cancelled class, and from the moment of cancellation none can be added.
Source: implied: U-6

### C-31: A member whose waitlist entry ends without a seat for one of the reasons below is sent a message naming the reason (leaving by their own choice and account closure, C-83, send none)
Observable: The reasons, each with its own message, are: booking closed with no seat; class cancelled; waitlist switched off for the class or everywhere; passed over (C-13); removed by staff. The message names the class, its start date and time, and the reason.
Source: implied: U-6

### C-32: Messages about the waitlist are delivered by the same channel (or channels) the app uses today for booking confirmations, and are also visible inside the app
Observable: A member who receives booking confirmations by email receives these by email; whatever the channel, the message is also readable in the app.
Source: choice: the request names no channel; reuse the existing one

### C-33: A promotion message states the class name, its start date and time in the studio's time zone, the location if the class has one, that the member is now booked, and how to cancel
Observable: The message contains each of those five parts.
Source: implied: U-2

### C-34: Times shown for waitlist purposes are in the same time zone the app uses to show class times today
Observable: A class shown as 18:00 in the class list is shown as 18:00 in the waitlist and its messages.
Source: implied: consistency

### C-35: The default maximum waitlist length is 10 entries per class occurrence
Observable: With 10 entries on a class, an 11th join is refused under C-22; with 9, the 10th succeeds.
Source: choice: bounded so a queue behind a class that will not open is not hopeless; 10 is a normal studio figure and is changeable (C-58)

### C-36: A waitlist entry asks for one seat, and a booking made by promotion holds exactly one seat
Observable: After a promotion the class has one fewer free seat and the member holds one booking in it. Unconfirmed: this assumes the app's bookings hold one seat each today; if a booking can hold several seats, a waitlist entry still asks for one.
Source: choice: the request gives no party sizes

### C-37: The events that free a seat, and so start a promotion under C-8, are exactly these five: a member cancels their own booking; staff cancel or remove a member's booking; staff raise the class's capacity (one free seat per seat added); a member's booking is released because their account is closed or suspended; a booking lapses under an expiry rule the app already has (for example an unpaid booking)
Observable: After any one of these, if the class has waitlist entries and a free seat, the first member able to book holds the seat (within the time in C-39). A seat that is free for any other reason (the class was never full) starts nothing.
Source: implied: "full classes don't turn people away" depends on every way a seat can open

### C-38: When staff raise capacity by n seats, up to n waitlisted members are booked, in waitlist order
Observable: Capacity 12 to 14 with waitlist A, B, C: A and B hold bookings, C is position 1.
Source: implied: C-37

### C-39: A promotion is complete, meaning the booking exists and is visible in the member's bookings, within 60 seconds of the seat becoming free
Observable: Within 60 seconds of a cancellation the promoted member sees the booking in their bookings area.
Source: choice: the request gives no time; 60 seconds is fast enough that a member never meets a stale "full" class for long; unconfirmed that the runtime meets it (see C-88)

### C-40: A promotion happens whether or not the member can receive the message about it
Observable: A member with no deliverable contact detail, or who has switched off messages, still holds the booking after promotion, and the message is present in the app.
Source: implied: C-32; a failed message must not undo or block the seat

### C-41: A member can join, leave and view only their own waitlist entries
Observable: A request by member M to join, leave or read the entry of member N is refused and changes nothing.
Source: implied: whoever acts must be allowed to; privacy

### C-42: Only a signed-in member account can hold a waitlist entry; visitors and guests without an account cannot
Observable: A guest cannot hold an entry; they are taken to sign in (C-27).
Source: choice: the request says "people" and the app books members; it gives no guest flow

### C-43: On a class page, a member already on the waitlist sees that they are on it, their position, and a leave control, and does not see a join control
Observable: Page shows e.g. "You're on the waitlist, position 3" and a leave control.
Source: implied: U-3, C-20

### C-44: A waitlist entry reserves no credit or allowance
Observable: A member with 1 credit left can be on three waitlists; the first promotion spends the credit; their turn on the other two finds them unable to book and they are passed over under C-13.
Source: implied: C-4 and C-11; credits are checked when the entry is created (C-23) and again at promotion (C-13)

### C-45: Waitlist management screens and actions (view, add, remove, settings, status, log) are available only to staff, being the people who can already manage class bookings in the app, and are refused to every other user; "operator" in this specification means such a staff user
Observable: A member who opens a staff waitlist screen, or sends a staff action, is refused and nothing changes. Which existing role or roles count as staff is unconfirmed; the role that can already cancel other members' bookings counts.
Source: choice: the request names no roles; reuse the existing permission

### C-46: The staff view of a class's waitlist lists every entry in position order, each with position, member name, the date and time the join was confirmed, and either "can book" or the reason from C-12 why the member cannot book now
Observable: A class with entries A (can book) and B (no credits left) lists A position 1 "can book", B position 2 "no credits left".
Source: implied: U-9

### C-47: Staff can remove any entry from a waitlist, and the entries behind it each move up one place
Observable: After removal the member is not on the waitlist and is sent the staff-removal message in C-31.
Source: implied: U-10

### C-48: Staff can add a member to a class's waitlist at the end, or at a position they give from 1 to one more than the current number of entries, and entries from that position onward move down one place
Observable: Adding at position 1 to a list of 3 gives positions 1 to 4, the added member being 1. Entering a position outside 1 to n+1 is refused and nothing changes. The join time the staff view shows for an added member is the time of the add.
Source: implied: U-10, U-11

### C-49: A member added by staff is sent a message naming the class, its start date and time, and their position
Observable: The member receives the message after staff add them.
Source: implied: the member must know they are in the queue

### C-50: An add by staff applies the same refusals as a member's own join (C-19 to C-24, C-26) and the same limit (C-35 and C-58), and cannot override any of them
Observable: Adding a member who is already booked, an already-listed member, a member who cannot book, or any member to a full waitlist is refused with the reason.
Source: implied: a rule is enforced the same on every path

### C-51: Staff cannot reorder existing entries; changing someone's place is done only by removing and re-adding them
Observable: No move, up or down control exists on the staff view.
Source: choice: deliberately left out; remove and add at a position (C-48) already covers it

### C-52: When the feature is first released, the waitlist is Off everywhere, and while it is Off no class shows a join control and no entry can be created
Observable: Immediately after release, a full class looks exactly as it did before release.
Source: implied: U-15, U-12

### C-53: The operator has a global switch for the waitlist; the settings screen shows its current state (On or Off), when it last changed and which staff user changed it
Observable: After turning it On the screen shows "On", the time, and the user's name.
Source: implied: U-12

### C-54: Turning the global switch On is refused, and the switch stays Off, if no message channel is configured for waitlist messages
Observable: The operator sees a message saying no channel is configured; the state remains Off.
Source: implied: a waitlist that promotes silently leaves members unaware of a booking; production requirement (see C-96)

### C-55: Turning the global switch On takes effect within 60 seconds: full classes then show the join control
Observable: Within 60 seconds of turning it On, a member reloading a full class sees the join control.
Source: choice: no restart or redeploy needed to turn it on

### C-56: Turning the global switch Off removes every waitlist entry on every class
Observable: After switching Off, no class has entries; the affected members are messaged under C-31, no join control is shown (C-52) and no booking has changed (C-104).
Source: implied: U-13, U-15; choice: entries are cleared rather than frozen because seats opening while frozen would go to others and break the queue

### C-57: The operator can switch the waitlist Off for one class occurrence, and On again; Off removes that class's entries
Observable: Other classes' waitlists are unchanged. Switching On again gives an empty waitlist. A class switched On has an open waitlist only while the global switch is also On.
Source: implied: U-13 "for one case"; choice: the granularity is one class occurrence, because that is the unit of C-1

### C-58: The operator can set the maximum waitlist length as a global setting (starting at the default in C-35) and, for one class occurrence, as an override of it; the allowed value is a whole number from 1 to 50, and clearing an override returns the class to the global value
Observable: Setting the global value to 15 makes a class with no override accept 15 entries; a class with an override of 5 accepts 5.
Source: choice: the request gives no number; 50 as the ceiling stops a runaway queue

### C-59: A value outside 1 to 50, or not a whole number, is refused when setting the limit, with a message, and the setting is unchanged
Observable: Entering 0, 51, 2.5 or text shows an error and the previous value remains.
Source: implied: C-58

### C-60: Lowering the limit below the number of entries a class already has removes no one; it only stops new joins until the entries fall below the limit
Observable: 8 entries, limit changed to 5: 8 entries remain, joins are refused (C-22) until there are fewer than 5.
Source: choice: removing people who were already promised a place would break trust

### C-61: The operator's status view shows: the global state (On or Off); the number of class occurrences that currently have at least one entry; the total number of current entries; and, for the last 24 hours, the number of promotions, the number of members passed over, and the number of messages that failed
Observable: After one promotion in the last 24 hours the promotion count reads 1.
Source: implied: U-12, U-14

### C-62: Every waitlist event is recorded with the time, the class occurrence, the member (where there is one), the event type, who acted (the member, a named staff user, or the system) and the reason where there is one
Observable: A log entry shows each of those fields. The event types are exactly: joined; left; added by staff; removed by staff; promoted; passed over; cleared at booking close; cleared at class cancellation; cleared by switch-off; removed at account closure; message sent; message failed; setting changed (which covers the global switch, a class's switch and either limit).
Source: implied: U-14

### C-63: Staff can filter the event log by class occurrence, by member, by event type and by date range, and combining filters shows only entries that match all of them
Observable: Filtering to event type "message failed" shows only failures; adding a member name narrows to that member.
Source: implied: U-14

### C-64: Log entries are kept for 12 months and may be deleted after that
Observable: An entry from 11 months ago can be found; one older than 12 months need not be.
Source: choice: the request gives no retention; 12 months covers a membership year

### C-65: A message that the channel fails to accept is tried three times in all: the second 5 minutes after the first failure and the third 15 minutes after the second failure
Observable: A channel that is down for an hour yields exactly 3 attempts and then one "message failed" event with the reason, which the status view counts (C-61).
Source: choice: the request is silent; a finite, short retry keeps one bad address from retrying forever

### C-66: Staff can cancel a booking made by promotion as an error, and doing so returns the credit or charge taken at promotion in full with no penalty
Observable: Staff cancelling with the "error" option see the member's credit count back where it was before the promotion (or the charge refunded); the seat then goes to the next entry under C-37. An ordinary staff cancellation follows the app's existing rules.
Source: implied: U-11

### C-67: Staff cancelling a promoted booking does not put that member back on the waitlist unless staff add them (C-48)
Observable: After the cancel, the member is not on the waitlist.
Source: choice: an automatic re-add would put them first in line for the seat that has just gone to someone else

### C-68: Classes that are already full when the feature is released or turned on start with an empty waitlist; nobody is added automatically, and no existing booking changes
Observable: A class with 12 of 12 bookings before release has 12 bookings and 0 entries after.
Source: implied: U-15

### C-69: Waiting lists the studio kept outside the app (a spreadsheet, a clipboard) are not imported; staff can enter them with C-48
Observable: No import control exists.
Source: choice: the request does not ask for it

### C-70: A booking made by promotion remains a valid booking, and still counts against the class's capacity, in the version of the app before the waitlist
Observable: After a rollback the promoted member still sees their booking and the class still counts them.
Source: implied: U-15 "go back to the version before"

### C-71: The documented way to go back is to turn the waitlist Off everywhere (C-56) and then roll back; entries left behind by a rollback without that step are ignored by the previous version and are cleaned up under C-72
Observable: After rolling back and later re-releasing, no member holds an entry for a class that has already closed.
Source: implied: U-15

### C-72: When the waitlist becomes active again, any class that has both free seats and entries is processed under C-8 within 60 seconds, and any entry belonging to a class whose booking has closed or that is cancelled is removed
Observable: After re-enabling, a class with a free seat and waitlist A gives the seat to A within 60 seconds.
Source: implied: C-71; restores the rule in C-102

### C-73: When two or more seats become free at the same time, each goes to a different waitlisted member in waitlist order, and no waitlisted member is booked twice
Observable: Two members cancel in the same second; waitlist A, B, C: A and B each hold one booking in the class, C is position 1.
Source: implied: a pair of concurrent cancellations

### C-74: When several members join at once and fewer places remain under the limit than there are joiners, exactly as many joins succeed as there are places and the rest are refused under C-22
Observable: 9 of 10 places taken, two members join at the same instant: one is at position 10, the other is told the waitlist is full; there are never 11 entries.
Source: implied: C-35 is a limit, and a limit that concurrent joins can exceed is not a limit

### C-75: An entry that has been left or removed (confirmed to the member or staff) is never promoted afterward
Observable: Member leaves at the same instant as the seat frees: if the leave was confirmed first, they hold no booking and were not charged. The case where the promotion came first is C-116.
Source: implied: a member leaving and a seat opening can coincide

### C-76: Once a class is cancelled, no booking is created in it by promotion
Observable: A class cancelled at 10:00:00 has no booking created for it at 10:00:01 from the waitlist.
Source: implied: cancellation arriving while a promotion is running

### C-77: A member who attempts a direct booking and loses a freed seat to the waitlist is told the class is full and is offered the join-waitlist control
Observable: The message says the class is full and the join control is present, subject to the refusals in C-19 to C-26.
Source: implied: C-9 meets direct booking

### C-78: Whether a waitlisted member can book is judged at their own turn against their bookings at that moment, and not against what was true when they joined
Observable: A joins waitlists for two overlapping classes, is promoted into the first; at their turn for the second, if the app forbids overlapping bookings, they are passed over under C-13 with the overlap reason.
Source: implied: two waitlists of one member meet

### C-79: A seat that frees before the class's booking close is processed under C-8 even if the processing finishes after the close; a seat that frees at or after the close is not offered to the waitlist
Observable: A seat freed 10 seconds before close ends up with the first waitlisted member; one freed 10 seconds after close does not.
Source: implied: booking close meets a promotion in progress

### C-80: When every waitlisted member has been passed over, the seat stays free and may be booked directly by anyone who can book
Observable: After all entries are removed under C-13, a member who is not on the waitlist can book the seat.
Source: implied: C-9 has an end; a seat must never be stranded

### C-81: A member who leaves and then joins again goes to the end of the waitlist and keeps nothing of their earlier position
Observable: A was position 1, leaves, rejoins a list of 4: A is position 5.
Source: implied: U-4 meets U-1; choice: no position memory, which would let a person hold a place while away

### C-82: Leaving, or being removed by staff, when the member is not on the waitlist changes nothing and tells the person that the member is not on the waitlist
Observable: A second "leave" click shows "not on the waitlist" rather than an error and changes no one else's position.
Source: implied: a repeated request

### C-83: When a member's account is closed, their waitlist entries are removed without a message, and the entries behind them move up one place
Observable: After closure the member has no entries and no message is sent to them.
Source: implied: C-37 account closed

### C-84: When a class is rescheduled to a different date or time, its waitlist entries stay, in the same order
Observable: Tuesday 18:00 becomes Tuesday 19:00: the entries and their positions are unchanged, and promotions stop at the new booking-close moment (C-25). If the new close is already in the past, C-29 removes the entries.
Source: implied: U-6; choice: keeping entries matches what the app does with the bookings of a rescheduled class (unconfirmed)

### C-85: While a class has as many bookings as its capacity or more (for example after staff lower the capacity below the bookings), no one is promoted
Observable: Capacity 12 lowered to 10 with 12 booked: the 12 stay booked and nobody is promoted; after 3 cancellations (9 booked) the one free seat goes to the first waitlisted member.
Source: implied: capacity change meets the waitlist

### C-86: After the operator has switched the waitlist Off (globally or for that class) and been shown that it is Off, no promotion happens afterwards in the scope switched off
Observable: A seat freed one second after the switch goes to no one from the waitlist; it can be booked directly.
Source: implied: C-56 and C-57 meet a promotion in progress

### C-87: When a promotion message has still not been delivered by the time the class has started, retrying stops, and a "message failed" event with the reason "class already started" is recorded
Observable: The member sees the promotion in the app; the log shows the event.
Source: choice: a late message about a class already under way would mislead more than inform

### C-88: A member's or staff user's action (join, leave, add, remove, cancel) returns its result within 5 seconds and does not wait for any message to be delivered
Observable: With the message channel down, a join still shows the member their position within 5 seconds. Reason: the app runs as a web service whose requests are time-limited and the message provider is an outside system that can be slow or fail; the host's exact request timeout is unconfirmed.
Source: choice: 5 seconds is the figure the specification sets; the host's own limit is unconfirmed

### C-89: A message caused by an event is handed to the message channel within 60 seconds of the event; the time the channel then takes to deliver it is outside this specification
Observable: The log shows "message sent" (accepted by the channel) within 60 seconds of the event.
Source: choice: the request gives no figure; delivery time belongs to the outside provider

### C-90: An event that causes many messages at once (for example switching the waitlist Off with up to 500 entries) sends every one, drops none, and hands all of them to the channel within 10 minutes; a message held back by the provider's sending-rate cap is sent later and does not use up the three attempts in C-65
Observable: Switching Off with 500 entries leads to 500 "message sent" events within 10 minutes. The provider's sending-rate cap is unconfirmed.
Source: choice: 500 and 10 minutes are the specification's figures; the provider's limit is unconfirmed

### C-91: From the booking-close moment onward, joins are refused, and a seat that frees from then on is not offered to the waitlist, whether or not any scheduled clean-up has yet run
Observable: At 17:30:01, with close at 17:30:00 and the clean-up job delayed, a join is refused under C-24 and a seat freed at 17:30:01 is not offered to the waitlist (a seat freed before 17:30:00 is still processed, C-79).
Source: implied: timers in a hosted runtime run late or not at all; the rule must not rest on one

### C-92: Entries remaining on a waitlist at booking close, or on a cancelled class, are removed within 5 minutes
Observable: At 5 minutes after close the class has no entries and the members have been sent the messages in C-31 (within the time in C-89).
Source: choice: the request gives no figure; C-91 makes the delay harmless

### C-93: After an outage or restart of the app, every class that has a free seat and entries is processed under C-8 within 60 seconds of the app being back, and entries of closed or cancelled classes are removed within 5 minutes of it being back
Observable: A seat freed during a 20-minute outage is given to the first waitlisted member within 60 seconds of recovery, provided the class has not closed in the meantime.
Source: implied: scheduled and triggered work does not run while the host is down

### C-94: A promotion is all or nothing: the booking, the credit or charge, and the removal of the entry either all happen or none does
Observable: If the charge fails, there is no booking, the member is passed over under C-13 with the reason that payment could not be taken, and no credit has been taken; after a crash part-way, no member is both booked and still listed, and no member is charged without a booking.
Source: implied: the runtime can fail at any step

### C-95: When a promotion fails for a reason that is not a member's own rule (a system error), the entry keeps its place and the promotion is retried, at least once every 60 seconds, until it succeeds or the class has started or been cancelled
Observable: A database error during promotion leaves the member at the same position; within 60 seconds it is tried again.
Source: implied: data must not be lost on the way

### C-96: Waitlist messages come from the same sender identity (address and domain) as the app's booking confirmations, and no new sending domain is introduced
Observable: The "from" address of a promotion message is the same as that of a booking confirmation.
Source: implied: before this could ship beyond development, messages must pass the same sender-authentication and spam checks that booking confirmations already pass; unconfirmed which these are

### C-97: Ordering of entries and booking close are decided by absolute time, so a daylight-saving change does not reorder entries or close a class an hour early or late
Observable: Entries confirmed at 01:30 (first occurrence) and 01:10 (second occurrence, after the clocks go back) are ordered by when they actually happened; a class's close moment remains the same instant it was before the change.
Source: implied: the studio has a local time zone

### C-98: When a member's account is deleted, their name and contact details are removed from the event log entries and replaced by "deleted member", and the entries otherwise stay
Observable: A log entry for a deleted member reads "deleted member" and still shows the event, time and class.
Source: implied: personal data of deleted members; unconfirmed whether a legal erasure rule applies

### C-99: Waitlist state shown to members (on the class page, in the waitlist list, in messages) is expressed in words, not only in colour or an icon
Observable: "Full — join the waitlist", "You're on the waitlist, position 3", "Booked" are readable text on the screen.
Source: implied: accessibility; choice: only the minimum is fixed

### C-100: Member-facing waitlist screens work on the same devices and browsers the app supports today, including phones
Observable: On a phone, the class page shows the join control and the waitlist list without sideways scrolling.
Source: implied: members book from phones; unconfirmed which the app supports today

### C-101: The staff view of a waitlist with 50 entries (the largest allowed, C-58) is shown within 3 seconds
Observable: Opening a 50-entry waitlist shows all 50 within 3 seconds.
Source: choice: the figure is the specification's

### C-102: For any class that is not yet past its booking close, once processing has finished (C-39) the class either has no free seat or has an empty waitlist; the two cannot both be false
Observable: No screen shows a class with a free seat and a waiting member who could book it, other than for up to 60 seconds after a seat frees, or while the waitlist is Off or its members are all unable to book.
Source: implied: the entire purpose, "full classes don't turn people away"

### C-103: Direct booking of a class that is not full behaves exactly as before, with the waitlist On or Off: same rules, same price, same confirmation
Observable: A member booking a class with free seats sees the same screens, charge and confirmation as before the release.
Source: implied: existing behaviour must hold

### C-104: Cancellation, late-cancellation, refund and credit rules for bookings are unchanged by the waitlist, and apply to every booking alike
Observable: A late cancellation of any booking is treated as it was before the release.
Source: implied: existing behaviour must hold

### C-105: While the waitlist is Off, the app's member-visible behaviour is the same as before the release
Observable: No screen, message or charge differs from the release before.
Source: implied: U-15; C-52

### C-106: A class that is full continues to appear in the class list, search and filters wherever it appeared before
Observable: Full class "Monday 18:00 Yoga" still appears in the list and is marked full.
Source: implied: existing behaviour must hold

### C-107: A promotion never takes the number of bookings in a class above its capacity
Observable: A class with capacity 12 never shows 13 bookings through any sequence of cancellations and promotions.
Source: implied: C-2, C-8

### C-108: A member is never both booked in a class and on that class's waitlist
Observable: After a promotion, a staff add, or a join, the member appears in exactly one of the two.
Source: implied: a person cannot be waiting for a seat they hold

### C-109: Each promotion takes the credit or charge exactly once
Observable: One promotion reduces credits by 1 (or makes one charge), however many times it is retried (C-95) or its message is resent.
Source: implied: a thing done twice that should happen once

### C-110: A promotion message is sent only after the booking exists
Observable: The member never receives a "you're booked" message for a seat they do not hold.
Source: implied: C-94

### C-111: Seats freed by each of the five events in C-37 are treated alike: same order, same eligibility, same messages
Observable: A seat freed by a staff cancellation and one freed by a member's cancellation go to the waitlist's first eligible member in the same way.
Source: implied: a rule enforced in one path and not another

### C-112: A waitlisted member's position changes only when an entry ahead of them is promoted, removed, or left, or staff add someone ahead of them
Observable: No other event alters positions.
Source: implied: C-6

### C-113: Joining or leaving a waitlist changes no booking, credit or charge
Observable: After joining and leaving, the member's credits and bookings are as they were.
Source: implied: C-4, C-44

### C-114: No message or screen shown to a member contains another member's name or contact details
Observable: Messages and the waitlist list show only the member's own information.
Source: implied: privacy

### C-115: Staff cannot edit or delete log entries within the retention period of C-64
Observable: No edit or delete control exists for log entries.
Source: implied: U-14, a record that can be changed cannot be relied on

### C-116: Where a promotion completed before a leave or a staff removal was confirmed, the leave or removal is answered by telling the person that the member is already booked in the class, and changes nothing
Observable: A member who clicks "leave waitlist" a moment after being promoted is told they are already booked (and can cancel the booking with the normal cancel action); their booking remains.
Source: implied: U-4 meets U-2; the other half of C-75

### C-117: When a class is rescheduled, every member on its waitlist is sent a message naming the new date and time
Observable: Tuesday 18:00 moved to Tuesday 19:00: each waitlisted member receives a message naming Tuesday 19:00 and can still leave.
Source: implied: C-84; U-6

### C-118: The staff view of a class with no waitlist entries says that no one is waitlisted
Observable: An empty waitlist shows a statement to that effect rather than a blank or an error.
Source: implied: U-9, the empty case

### C-119: A member's waitlist list, when they are on no waitlist, says that they are on none
Observable: The list shows a statement to that effect rather than a blank or an error.
Source: implied: U-3, the empty case

### C-120: There is no limit on the number of different classes a member may be waitlisted for at once
Observable: A member can hold entries on 10 classes at once; each follows its own order and its own rules.
Source: choice: the request sets none, and C-44 and C-78 already settle what happens when entries compete

