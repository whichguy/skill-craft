# Passes

Context found: the working directory held no app and no commits, so every existing behaviour (capacity, booking, cancellation, staff, email, credits, reminders) is an assumption. Where a clause leans on an existing rule whose detail I cannot see, the clause says so (C-23, C-57, C-74, C-75, C-78, C-94).

## Pass 1 — the ground
Added U-1..U-13 and C-1..C-40: join, check position, leave, promote on cancellation, pass over an ineligible member, unchanged booking, staff view/remove/configure, class changes (capacity, cancel, move), a promoted member cancelling, deploy/rollback, history. Covers the ordinary use, edges (empty and full waitlist, double join), unhappy paths (class not full, already booked, ineligible member), and the operator's work.
Found nothing on: concurrency, time zones, account removal, notification failure (left to later passes).

## Pass 2 — what each sentence takes for granted
Asked of "our class booking app", "full classes" and "turn people away" what must already be true. Added U-14 (someone who may not join) and U-15 (a waiting member's account goes away), and C-41..C-57: signed-in members only; who may join (suspension, membership, credit deferred to the turn); cancelled or started classes; what the confirmation must tell the member; privacy of other members' names; why no join action is offered; waitlist off or lowered with people waiting; capacity lowered below bookings; one place per entry; account removal; no email address; message preferences; time zone; capacity 0; cancellation cutoff for promoted bookings.
Found nothing on: further identity or visibility questions beyond C-46.

## Pass 3 — where the parts meet
Walked pairs: cancel with cancel, join with join, double-delivered cancel, leave/staff removal/class cancel/start time each against a promotion, a failure while booking, a retried booking, message failure against the next promotion, other booking routes (staff on behalf, any route) against the queue, overlapping classes, one promotion against other waitlists. Added C-58..C-73 (and C-74 for ordinary cancellation staying the same).
Found nothing on: capacity change against concurrent joins (covered by C-26 and C-59).

## Pass 4 — the runtime's own rules
The runtime is not visible, so these are stated as forced behaviour with unconfirmed figures marked: request time limit (C-75, figure unconfirmed), work that happens with no one visiting (C-76), daylight saving (C-77), email provider throttling (C-78, limit unconfirmed), the bounded waitlist capacity of 0 to 100 (C-79), state surviving restarts and deploys (C-80), shipping without a working email channel (C-81), retention of personal data (C-82), a request rate limit (C-83), roll forward after rollback (C-84).
Found nothing on: database or hosting specifics the request does not name.

## Pass 5 — what must not change, and what must never happen
Added C-85..C-91: never over capacity, keep trying down the list until someone is booked, positions always 1..n, departures only for eight named reasons, not-full classes unchanged, existing bookings never touched, reminders for promoted members.
Found nothing on: charging (already C-28, C-29, C-66).

## Pass 6 — grind: read as the builder
Fixed: C-8 and C-26 disagreed about whether a free place that someone is waiting for counts as free (now C-26 defines it; C-3 and C-8 use it); C-10 and C-13 observables; C-18 rewritten as a closed list of four routes; C-20 message parts completed; C-25 now says which condition applied; C-36/C-37 each split in two; C-38 now lists nine events including those added in passes 2 and 3; C-39 no longer smuggles in a default (moved to C-101); C-76 split from promotion timing; C-88 reworded. Added C-92..C-102: which departures are messaged, staff's count view, who "staff" is, the complete list of staff controls and what is deliberately left out, what "message" means, empty list, waiting member booking directly, setting capacity, who may change a waitlist, default on, rejoining after removal.
Found nothing on: nothing recorded as found-nothing; this pass found several problems.

## Pass 7 — grind: unhappy paths, ends and numbers
Looked for each use case's unhappy path, each state's end, each number. Found C-73 contradicted C-95 (staff adding a member to a waitlist) and fixed it; C-69 charging wording fixed. Added C-103 (stale staff removal) and C-104 (empty staff view). Confirmed ends: waitlist entries (C-88), history (C-82, 90 days), retries (C-67, until class start), rate counter (C-83, one minute). Confirmed numbers: 10 and 0..100 (waitlist capacity), 60 seconds (C-24, C-76 uses 1 minute), 90 days, 30 requests a minute.
Found nothing on: number gaps; 104 clauses and 15 use cases, numbered with no gaps or duplicates (checked).

## Pass 8 — the stopping pass
Read all of C-1..C-104 and U-1..U-15 again as the one who will be blamed, looking for: an Observable that cannot be observed; a word two readers would read differently ("full", "place", "staff", "message" are each defined by C-1, C-26, C-94, C-96); a number nobody wrote; a use case with no unhappy path; a piece of state with no end; a silent decision not marked as a choice; a clause that is two; a contradiction between clauses. Found nothing a builder would otherwise have got wrong.
