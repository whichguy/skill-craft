# Passes

Starting point: the working directory held no app, code or earlier documents (an empty git repository). Everything about the existing booking app (its members, staff, capacity, notices, fees) is therefore taken as "whatever the app already does today", and the spec is written against that.

## Pass 1: the ground
Added U-1 to U-10 and C-1 to C-32: joining a full class, seeing position, automatic promotion, leaving, refusals, endings with notices, staff view and management, operator switch, existing data, revert. Found nothing on: concurrency, definitions of words such as "full" and "eligible", limits, runtime (left for later passes).

## Pass 2: what each sentence takes for granted
Added C-33 to C-52. The words the request leaves undefined became clauses: "full" (C-33), unlimited classes (C-34), one spot per entry (C-35), one occurrence per entry (C-36), "eligible" (C-37), what promotion charges (C-38), time zone (C-39), channels and opt-out (C-40, C-41), failed notice (C-42), notice time (C-43), penalty at an automatic booking (C-44), staff history and retention (C-45, C-46), who staff are (C-47), limit range (C-48), moved classes (C-49, C-50), leaving always possible (C-51), when the join control shows (C-52). Found nothing on: the request sentence "so full classes don't turn people away" beyond what C-1 and C-52 say.

## Pass 3: where the parts meet
Added U-11, U-12 and C-53 to C-66: two joins, two cancellations, the same cancel or leave twice, a leave racing a promotion, staff removal racing a promotion, cancel racing promotion, account closure, booking by other means, independent entries, closing while the feature is off, entries visible while off, removing a member who is not there. Found nothing on: a promoted member being on other lists (kept independent as a choice, C-63).

## Pass 4: the runtime's own rules
The runtime is not named in the request; I assumed a hosted service used from browsers and phones with email and phone-alert providers. Added C-67 to C-75: stale pages, server clock, undeliverable notices (provider limits marked unconfirmed), bulk changes inside a hosted request's time (60 s, marked unconfirmed), authenticated sending domain, encrypted connections, account deletion versus retained history, accessibility, a join rate limit. Found nothing on: storage engines and queue technologies (not a clause by the brief).

## Pass 5: what must not change, what must never happen
Added C-76 to C-86: booking with a free spot unchanged, cancelling with no waitlist unchanged, existing cancellation rules, never over capacity, one spot one promotion, same rules on every path, ownership and staff-only actions, all-or-nothing promotion, a fault never costs a turn, no other member's details in any notice, one notice per event. Found nothing on: any existing behaviour beyond booking and cancelling, since none is visible.

## Pass 6: grind (first full read as the builder)
Found and fixed: a rate limit that contradicted "leaving is always possible" (C-75, C-51); a reason in the ending notice that contradicted "switching off keeps entries" (C-22, C-29); clauses that joined two behaviours (C-26, C-29, C-39, C-40 split, with C-87, C-88, C-89, C-91 added); dimensions without full lists (C-6, C-17, C-33, C-45); an "implied" clause that went beyond the request (C-8, with C-92 as a choice); the claim that a spot is held for the line while the feature is off (C-15, C-57, C-88); ambiguous "edit classes" for staff (C-47); behaviour after revert-and-return (C-90). Added C-87 to C-92.

## Pass 7: grind (second full read)
Found and fixed: position numbers and automatic booking presented as implied by the request when another correct product could do otherwise, so now choices (C-2, C-5, C-10); a close-time removal that said "at the moment" and could not be observed (C-20, C-61, bound by C-70); undefined words "occurrence" and "free spot" (C-33, C-36); in-app information with no end (C-93). Added C-93.

## Pass 8: the pass that found nothing to add
Read the whole specification once more as the builder who will be blamed, looking for: an Observable that cannot be observed; a word two readers would read differently; a number implied but not written; a use case with no unhappy path; a state with no end; a decision made silently; a clause that is two; a contradiction between clauses. Also checked mechanically: 93 clauses and 12 use cases numbered without gaps, every clause with an Observable and a Source, every cross-reference pointing at an existing item. Changed nothing in `spec.md`. This is the stopping pass.

## Deliberately left open (not fixed because the request does not need them fixed)
- Wording, layout and language of every message and control.
- Whether the app's usual booking confirmation is also sent for a promoted booking.
- Whether members are told when their position improves (no clause requires it or forbids it).
- Whether members can see how many people are waiting in total.
- Whether staff can add a member to a waitlist or reorder one (the spec lists the staff actions, C-47, and does not require these).
- Which condition is named when several refusals hold at once (C-14 requires naming at least one).
- Storage, queuing and scheduling technology.
