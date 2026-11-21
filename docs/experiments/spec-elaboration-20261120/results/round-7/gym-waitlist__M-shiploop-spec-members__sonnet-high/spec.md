# Class Booking App: product specification

Living contract for the class booking app. This revision adds the **waitlist** capability and states what the
booking behaviour it touches must keep doing. Structure and technology choices live in `architecture.md` (`AD-<n>`),
never here. Product decisions are `PD-<n>`.

## Evidence limits (read first)

- **No repository, no earlier spec, no discovery or research result, no selected baseline** was available to this
  run. Nothing below was observed in the existing app. Every statement about "today's" behaviour is an
  **assumption** (labelled `ASM-<n>`) or an **open gap**, never an observation.
- Where a requirement depends on existing behaviour (how booking, cancellation, eligibility, notification and
  identity work), it says so and keeps the dependent work unready until a baseline is captured (G-0, under R-9).
- Source of intent: the request of **2026-11-21**: "Add a waitlist to our class booking app so full classes don't
  turn people away."
- Nothing here claims implementation or test success. Every check is **planned**; every expected result for a worked
  example is `NOT-REPLAYED` (see "Worked example" at the end).

### Assumptions about the existing app (to be confirmed or corrected by a baseline)

| ID | Assumption | If wrong |
|---|---|---|
| ASM-1 | The app has **members** who sign in and book places in **classes**; a class has a start instant and a **capacity** (a whole number ≥ 1). | R-1..R-10 need re-derivation. |
| ASM-2 | A class is **full** when confirmed bookings = capacity; today a full class shows a dead end ("Full"/disabled) and refuses booking. This is what "turn people away" means. | R-8's before-state changes. |
| ASM-3 | Members can cancel their own booking; staff can cancel a booking and change a class's capacity or cancel a class. | Triggers in R-4/R-7 shrink to the ones that exist. |
| ASM-4 | Booking already enforces eligibility rules (unknown set: e.g. membership status, credits, time conflicts). | R-4's eligibility clause becomes trivially true. |
| ASM-5 | The app already has some member-facing notification channel (unknown: email, push, in-app). | R-6 falls back to in-app status only. |
| ASM-6 | The client is a graphical app (web or native, unknown) used by members on phone-sized and larger screens. | NFR-UI criteria apply to whichever surface exists. |

## Product decisions (defaults taken unattended; owner may overturn)

| ID | Decision (default) | Why | Who it affects |
|---|---|---|---|
| PD-1 | **Automatic promotion**: when a place opens, the first eligible waitlisted member is booked automatically; no claim window or "confirm within N minutes" step. | The request names no timer; a claim window needs a bound the owner has not given (invent no bound), a scheduler and more states. Auto-promotion keeps places filled up to class start. | R-4, R-6, NFR-time. **Open for owner confirmation (G-4a).** |
| PD-2 | Waitlist order is **first-come-first-served** by the order the service accepts joins. No priority, no paid priority. | Simplest fair rule; the request is silent. | R-2 |
| PD-3 | A member who is **ineligible at promotion time** is skipped and removed from that waitlist with a notice; the next member is tried. | Keeps the queue moving; a skipped-but-kept entry would be retried forever. | R-4, R-6 |
| PD-4 | **Leaving and re-joining puts the member at the tail.** | Prevents holding a position while undecided. | R-3 |
| PD-5 | Members see **their own position** and the **total waiting count**, never other members' identities. | Count helps the join decision; identities are other people's data. | R-2, R-10 |
| PD-6 | Waitlist entries **end at class start**; promotions can occur at any time before start. | Auto-promotion needs no reaction window, so no pre-start cutoff is needed. | R-4, R-7 |

## Request outcomes → requirements

| Outcome (from the request) | Requirements |
|---|---|
| A. A member who finds a class full is not turned away: they can join a waitlist. | R-1, R-8 |
| B. When a place opens the waitlisted member actually gets it, fairly and without being beaten by someone booking directly. | R-2, R-4, R-5, R-6 |
| C. (Implied) A waitlisted member can change their mind and the waitlist ends cleanly with the class. | R-3, R-7 |
| D. (Implied) Nothing the app did before breaks; nobody's data is exposed by the new feature. | R-9, R-10 |

Out of scope for this request, listed under the R it bounds: payments, credits and late-cancel fees (R-4); staff
waitlist-management screens and manual promotion/reordering (R-2, R-10); waitlists across recurring series (R-1);
SMS or any new notification channel (R-6); analytics/reports (R-7); per-member limits on how many waitlists to join
(R-1, gap G-1b).

## Requirements

Acceptance-line key: **P** positive, **F** failure, **B** boundary, `n/a: <reason>` where a kind says nothing the
others do not. Each line names the **surface** where it is observed and **how it is confirmed**. Locators like
`R-1:A2` name an acceptance line. Error names (`NOT_FULL`, ...) are logical outcomes; mapping them to transport
codes is a plan choice (`architecture.md`).

Sets used throughout (members of each, so a check can cover each group):
- **Class state**: *open-with-space* (confirmed < capacity, waitlist empty), *full-open* (confirmed = capacity,
  before start, not cancelled), *started/ended*, *cancelled-by-staff*.
- **Member's relation to a class**: *none*, *booked*, *waitlisted*, *waitlisted-then-promoted* (a booked member).
- **Actors**: signed-in member (self), a different signed-in member, signed-out visitor, staff (existence per ASM-3).
- **Spot-opening triggers**: (T-a) member cancels own booking; (T-b) staff cancels a booking; (T-c) staff increases
  capacity by k ≥ 1; (T-d) any other existing removal of a confirmed booking (e.g. no-show/expiry rules, if any
  exist: unknown, G-0).

### R-1 Join the waitlist of a full class

- **Basis:** request 2026-11-21 ("full classes don't turn people away"). **Change:** add. **Preserved:** booking a
  class that has space is unchanged (R-9). **Source locators:** none (no baseline). **Evidence limit:** ASM-1/2
  unverified. **Pending:** implementation and all checks below.
- **Behaviour:** a signed-in member who is *none* for a *full-open* class can join its waitlist; the service
  appends them at the tail (R-2) and returns the entry with their position.
- **Boundaries:** exactly full (confirmed = capacity) allows joining; one below capacity does not (`NOT_FULL`).
  A class whose waitlist is non-empty counts as full for joining even if a place is momentarily free (cannot
  persist: R-5). *Waitlist length cap:* unresolved (G-1a); interim behaviour is **no cap**.
- **Error behaviour (state unchanged in all):** `NOT_FULL` (member is told to book directly), `ALREADY_BOOKED`,
  `CLASS_CLOSED` (started/ended or cancelled), `UNAUTHENTICATED`, `NOT_FOUND` (no such class), `WAITLIST_FULL`
  only once a cap exists (G-1a). A repeat join by an already-waitlisted member is **idempotent**: returns the
  existing entry and position, creates no second entry.
- **Consumer outcome:** the member sees themselves on the waitlist with a position; the class card no longer ends
  in a dead end.
- **Acceptance**
  - R-1:A1 **P**: class C-101 capacity 2 booked {Ana, Ben}; Cai joins → entry created, position 1, waitlist [Cai],
    confirmed bookings still {Ana, Ben}. Surface: member client + service operation. Confirmed: API-level case
    through the real service, then one browser/app journey.
  - R-1:A2 **P (idempotent replay)**: Cai joins C-101 again → same entry, position 1, waitlist still has one Cai.
    Same surface/confirmation as A1.
  - R-1:A3 **F**: join when the class is *open-with-space* (C-101 capacity 4, 3 booked) → `NOT_FULL`, nothing created;
    when Ana (booked) joins → `ALREADY_BOOKED`; class started or cancelled → `CLASS_CLOSED`; signed-out →
    `UNAUTHENTICATED`; unknown class id → `NOT_FOUND`. Confirmed: API-level cases, one per error; each asserts no
    entry exists afterwards.
  - R-1:A4 **B**: capacity 4 with 3 booked → `NOT_FULL`; the 4th booking is made → join succeeds. Capacity-1 class
    works the same. Confirmed: API-level.
  - R-1:A5 **F (race)**: a member's join arrives when a place just opened and the waitlist was empty: the service
    decides from the state at the moment it processes the request; if the class is no longer full the result is
    `NOT_FULL` and the client refreshes to offer "Book". Confirmed: concurrency case (see NFR-conc).
- **Open gaps:** G-1a waitlist length cap (value unresolved; owner: product owner; interim: no cap, due before
  release planning). G-1b limit on how many waitlists one member may join (unresolved; interim: none).
  Series/recurring-class handling is out of scope (each class instance has its own waitlist).
- **State and data:** creates one waitlist entry {class, member, join order, status}; owner and authority: the
  service's booking store (AD-1); before: member has no entry; after: exactly one *active* entry; invariants I1-I4
  (R-5) hold; recovery: a failed write creates no entry and tells the member (no partial entry).

### R-2 Waitlist order and the member's position

- **Basis:** request 2026-11-21 (fairness is implied by "waitlist"); PD-2, PD-5. **Change:** add. **Evidence
  limit:** none about existing app. **Pending:** implementation and checks.
- **Behaviour:** entries are ordered by the order the service accepted the joins (a service-assigned sequence,
  not a client or wall-clock time, so two joins in the same millisecond still have a defined order). A member's
  position is 1-based and always contiguous; when an entry ahead leaves, is promoted, is skipped, or expires,
  the positions behind close up. The member sees their own position and the total waiting count (PD-5).
- **Boundaries:** position 1 is the next to be promoted. Position and count are correct at the time of read;
  **real-time push is not required**: they are correct on every load/refresh and after the member's own actions
  (G-2: confirm whether live updates are wanted; interim: refresh on load and on app return to foreground).
- **Error behaviour:** reading position for a class the member is not waitlisted for → `NOT_ON_WAITLIST` (no
  position for others is ever returned); signed-out → `UNAUTHENTICATED`.
- **Consumer outcome:** a member sees e.g. "You're 2nd of 3 on the waitlist".
- **Acceptance**
  - R-2:A1 **P**: C-101 (cap 2, booked {Ana, Ben}); Cai, Dee, Eli join in that order → positions 1, 2, 3; each
    member reads only their own position; every reader sees count 3. Confirmed: API-level + client check.
  - R-2:A2 **P**: waitlist [Dee, Eli] (worked example S3); Dee leaves (R-3) → Eli's position changes 2 → 1 and
    positions stay contiguous. Confirmed: API-level.
  - R-2:A3 **F**: Fay (not waitlisted) asks for a position → `NOT_ON_WAITLIST`; Fay can never obtain Cai's,
    Dee's or Eli's identity or position from any read. Confirmed: API-level, different-member token.
  - R-2:A4 **B**: simultaneous joins by two members → two distinct positions with no duplicate or gap
    (positions {n, n+1}). Confirmed: concurrency case (NFR-conc).
- **Out of scope:** priority tiers, manual reordering, staff override (PD-2).
- **State and data:** order is part of the entry; owner: booking store; concurrent joins resolve by the store
  assigning the sequence (a requirement on atomic assignment, mechanism in AD-1).

### R-3 Leave the waitlist

- **Basis:** request 2026-11-21 (implied; a waitlist without exit traps members); PD-4. **Change:** add.
  **Pending:** implementation and checks.
- **Behaviour:** a waitlisted member can leave at any time before class start. The entry ends with reason `left`;
  members behind move up; no booking is created or altered.
- **Boundaries:** the last waitlisted member leaving leaves an empty waitlist (class stays full). Re-joining after
  leaving creates a new entry at the **tail** (PD-4).
- **Error behaviour (state unchanged):** member is not on the waitlist (including a second leave) →
  `NOT_ON_WAITLIST`; class started/cancelled → `CLASS_CLOSED` (entry already ended by R-7); another member's
  entry → treated as `NOT_ON_WAITLIST` (existence of others' entries is not revealed); signed-out →
  `UNAUTHENTICATED`.
- **Consumer outcome:** the member sees the class as joinable again and the waitlist count down by one.
- **Acceptance**
  - R-3:A1 **P**: S3 of the worked example: Dee leaves a list [Dee, Eli] → LEFT, list [Eli], Eli position 1.
  - R-3:A2 **F**: Dee leaves again → `NOT_ON_WAITLIST`, list unchanged; Fay leaves Cai's entry →
    `NOT_ON_WAITLIST`, Cai's entry intact. Confirmed: API-level.
  - R-3:A3 **B**: waitlist [Cai, Dee, Eli]; Cai leaves then re-joins → order [Dee, Eli, Cai], Cai position 3.
    Single-entry waitlist: leaving empties it. Confirmed: API-level.
- **State and data:** entry changes active → ended(`left`); terminal record kept per R-7; no partial effect.

### R-4 Automatic promotion when a place opens

- **Basis:** request 2026-11-21 (the point of a waitlist); PD-1, PD-3, PD-6. **Change:** add. **Evidence limit:**
  eligibility rules and cancellation consequences of the existing app unknown (ASM-3/4). **Pending:**
  implementation and checks.
- **Behaviour:** whenever a *full-open* class gains k ≥ 1 free places through any spot-opening trigger (T-a..T-d),
  the service, **as part of the same operation that opened the place** and before it returns, promotes up to k
  waitlisted members in order: for each head-of-queue member it re-checks the member's *current* eligibility
  using the **same rules as a direct booking** (ASM-4); an eligible member becomes a confirmed booking (entry
  ends `promoted`); an ineligible member is skipped, their entry ends `ineligible` (PD-3) and the next is tried.
  Promotion stops when places or waiting members run out.
- **Boundaries:** (T-c) capacity +3 with 2 waiting promotes both and leaves 1 place for direct booking (R-5);
  capacity +1 with 3 waiting promotes only position 1. If the list holds only ineligible members, all are
  skipped and the class returns to *open-with-space*. No promotion for a class that has started or been
  cancelled (R-7). *Spot opening inside any late-cancel/penalty window of the existing app:* the promoted booking
  is subject to whatever the existing rules say; the rule itself is unknown (G-4b).
- **Error behaviour:** if the promotion write fails, the opening event and the promotion are **both** not
  applied (single unit of work) and the caller gets the failure: the class never shows a free place with a
  waiting member (R-5:I1). A member who cannot be notified is still promoted (R-6).
- **Consumer outcome:** the promoted member finds a confirmed booking in their bookings and is told (R-6); the
  member behind sees their position drop by one.
- **Acceptance**
  - R-4:A1 **P (T-a)**: worked example S2: C-101 cap 2 booked {Ana, Ben}, waitlist [Cai, Dee, Eli]; Ben cancels →
    Cai booked, bookings {Ana, Cai}, waitlist [Dee, Eli], Dee position 1. Confirmed: API-level through the real
    service + a client journey of Ben cancelling and Cai seeing the booking.
  - R-4:A2 **P (T-b)**: same with staff cancelling Ben's booking (if ASM-3 holds).
  - R-4:A3 **P/B (T-c)**: S4: waitlist [Eli], bookings {Ana, Cai}, capacity 2→4 → Eli promoted, 1 place free,
    waitlist empty; the pre-promotion waitlist of 3 with +1 place promotes exactly one.
  - R-4:A4 **F (ineligible)**: S7: cap 1, booked {Ana}, waitlist [Gus, Hal], Gus ineligible when Ana cancels →
    Gus skipped (entry `ineligible`), Hal promoted, bookings {Hal}, waitlist []. Confirmed: needs a concrete
    ineligibility rule from the baseline (G-4c); until then **NOT-REPLAYED**.
  - R-4:A5 **B (two openings)**: S6: cap 2 booked {Ana, Ben}, waitlist [Cai]; Ana and Ben cancel, in either
    order → bookings {Cai} plus one free place; Cai is promoted exactly once; Fay can then book directly.
  - R-4:A6 **F (atomicity)**: injected write failure during promotion → the cancel is also not applied
    (Ben still booked, Cai still waitlisted) and the caller sees an error. Confirmed: failure-injection test at
    the real store boundary.
  - R-4:A7 **n/a (class started)**: covered by R-7:A2.
- **Open gaps:** G-4a owner confirmation of auto-promotion vs claim window (PD-1); until answered the claim
  window is **not** built. G-4b late-cancel/penalty/credit behaviour for a promoted booking made close to start
  (unknown; owner: product owner; interim: apply existing booking rules unchanged). G-4c the set of eligibility
  rules in the existing booking path (needs baseline).
- **Out of scope:** payments, credit deduction or fees specific to waitlist (the existing booking rules apply as
  they do to direct bookings).
- **State and data:** changes bookings (adds one per promoted member) and entries (active → promoted/ineligible)
  in one unit of work; before: confirmed = capacity − k, waitlist non-empty; after: I1-I4 hold; recovery as in
  error behaviour above.

### R-5 Reserved places and capacity integrity

- **Basis:** request 2026-11-21 ("full classes don't turn people away" is not met if a direct booker can take the
  place the waitlisted member was promised). **Change:** add. **Pending:** implementation and checks.
- **Behaviour:** these invariants hold for every class before its start at every instant a request can observe:
  - **I1** a non-empty waitlist implies confirmed = capacity (places go to the waitlist first);
  - **I2** no member is both booked and waitlisted for the same class;
  - **I3** confirmed ≤ capacity, even under simultaneous requests;
  - **I4** active positions are exactly 1..n with no gaps or duplicates.
  Consequently a direct booking attempt on a class with a non-empty waitlist is refused as `CLASS_FULL` and is
  offered a join (R-1); direct booking only succeeds when the waitlist is empty and a place is free.
- **Boundaries:** capacity 1; two simultaneous cancellations; a direct booking racing a cancellation (S5).
  If staff **reduce** capacity below confirmed bookings, existing behaviour decides what happens to the
  bookings (unknown, G-5); the waitlist rule is only that no promotion happens until confirmed < capacity.
- **Error behaviour:** a refused direct booking changes nothing and says `CLASS_FULL`.
- **Consumer outcome:** nobody sees a free place that a waitlisted member is owed; two members never both hold
  the last place.
- **Acceptance**
  - R-5:A1 **P/F**: S5, both orderings of {cancel Ana, Fay books} on cap 1, booked {Ana}, waitlist [Cai] →
    in both, bookings {Cai}, Fay gets `CLASS_FULL`, waitlist []. Confirmed: concurrency case against the real
    store (NFR-conc).
  - R-5:A2 **F**: S1/S2: Fay tries to book while the waitlist is non-empty → `CLASS_FULL`, nothing created.
  - R-5:A3 **B**: 10 concurrent direct bookings on a class with 1 free place and an empty waitlist → exactly
    1 `BOOKED`, 9 `CLASS_FULL`, confirmed = capacity. (10 is a test workload, not a product limit.)
  - R-5:A4 **F (I2)**: a booked member cannot join (R-1:A3) and a waitlisted member cannot book directly
    (`ALREADY_WAITLISTED`), so no member is ever both. Confirmed: API-level, both directions, state unchanged.
- **Open gaps:** G-5 existing behaviour when capacity is reduced below confirmed bookings (needs baseline).
- **State and data:** I1-I4 are the cross-entity invariants over {bookings, entries}; concurrency resolved by
  serialising changes per class (mechanism AD-1).

### R-6 Notifying members of waitlist outcomes

- **Basis:** request 2026-11-21 (a member who is promoted must be able to learn it); PD-1/PD-3. **Change:** add.
  **Evidence limit:** the existing channel is unknown (ASM-5). **Pending:** implementation and checks.
- **Behaviour:** after the promotion commits, the promoted member is told: class name, start time, "you were
  promoted from the waitlist". A member skipped as ineligible is told the reason in category terms. The
  booking, not the message, is the truth: it appears in the member's bookings regardless of delivery. The
  in-app marker "promoted from waitlist" is always available; any existing outbound channel (ASM-5) is used in
  addition. **No new outbound channel is added** by this request.
- **Boundaries:** one notification per promotion (a retry never produces a second to the member); no
  notification for position changes alone.
- **Error behaviour:** delivery failure does **not** undo the promotion and does not block the cancel that
  caused it; the failure is recorded on the entry/event so staff can see it; retry policy: unresolved (G-6;
  interim: one attempt, failure recorded).
- **Consumer outcome:** the promoted member sees the booking and the marker on opening the app, and receives
  the message where the app already sends them.
- **Acceptance**
  - R-6:A1 **P**: R-4:A1 → Cai's bookings view lists C-101 with the promotion marker; the outbound message (if a
    channel exists) names C-101 and its start. Confirmed: client journey + test sink for the channel.
  - R-6:A2 **F**: channel failure injected → Cai still booked, entry/event records the failed notification,
    Ben's cancel still succeeded. Confirmed: failure-injection at the notification boundary.
  - R-6:A3 **B**: a promotion that retries internally produces exactly one message. Confirmed: test sink count = 1.
- **Open gaps:** G-6 existing channel and retry policy (needs baseline; owner: product owner).

### R-7 End of a waitlist entry and its record

- **Basis:** request 2026-11-21 (implied lifecycle); PD-6. **Change:** add. **Pending:** implementation and checks.
- **Behaviour:** an active entry ends in exactly one terminal reason: `promoted`, `left`, `ineligible`,
  `expired` (class started), `class_cancelled` (staff cancelled the class), or `member_removed` (account
  deleted/deactivated per existing behaviour, G-7a). Ended entries are no longer shown to members as waitlisted.
  Class cancellation notifies waitlisted members the same way booked members are notified (existing behaviour,
  ASM-5). The terminal record keeps {class, member id, reason, ended-at}: no names, emails or free text.
- **Boundaries:** at class start no promotion happens afterwards; I1 holds for classes before start (an
  entry never outlives start: evaluated lazily at read/promotion time against the class start instant, so no
  clock job is needed for correctness: AD-2). Retention period of terminal records: unresolved (G-7b).
- **Error behaviour:** a join/leave on an ended class → `CLASS_CLOSED`, nothing changes.
- **Consumer outcome:** a started or cancelled class shows no waitlist; members who were waiting see why (class
  cancelled or started without a place).
- **Acceptance**
  - R-7:A1 **P**: staff cancel class C-101 with waitlist [Cai, Dee] → both entries end `class_cancelled`; no
    bookings are created; both are notified. Confirmed: API-level + notification sink.
  - R-7:A2 **B/F**: C-101 cap 1 booked {Ana}, waitlist [Cai]; start time passes → Cai's entry reads `expired`;
    a join by Dee → `CLASS_CLOSED`; Ana cancelling afterwards (if the existing app still allows it) does not
    promote Cai. Confirmed: test with a controllable clock/fixture start instant, at the real service.
  - R-7:A3 **P**: every terminal reason is reachable and recorded once: left (R-3), promoted/ineligible (R-4),
    expired, class_cancelled. `member_removed`: **NOT-REPLAYED** pending G-7a.
- **Open gaps:** G-7a behaviour on account deletion/deactivation (unknown). G-7b retention period (owner: product
  owner; do not invent; interim: keep, with no personal data beyond the member id).
- **Out of scope:** analytics/reporting on waitlists.
- **State and data:** entries move active → terminal exactly once; terminal records are never reactivated.

### R-8 Full classes show the waitlist, not a dead end

- **Basis:** request 2026-11-21 (the primary outcome as seen by a person). **Change:** add. **Evidence limit:**
  the existing UI, platform and visual identity are unknown (ASM-2, ASM-6). **Pending:** implementation and
  checks.
- **Behaviour:** in every place a class is shown with its booking action, the member sees one of: **Book**
  (open-with-space), **Join waitlist** (full-open, not waitlisted), **On waitlist: 2nd of 3** with a **Leave
  waitlist** action (waitlisted), **Booked** (booked, incl. promoted, with the marker), or a closed state
  (started/cancelled). The count of people waiting is shown on a full class. A member's waitlists are listed
  together in one place (e.g. alongside their bookings).
- **Boundaries:** state shown follows the service's answer; it is never inferred locally. While an action is
  in flight the control shows a pending state and is not clickable twice; the position is displayed only after
  the service confirms it. If the response says the class has changed (`NOT_FULL`, `CLASS_FULL`, `CLASS_CLOSED`)
  the view refreshes to the true state and says what happened.
- **Error behaviour:** network or server failure → an error message with a retry action that stays visible
  (not a toast that vanishes), the control returns to its prior state and no position is shown.
- **Consumer outcome:** in the "class is full" situation the member can act, and always knows where they stand.
- **Acceptance**
  - R-8:A1 **P**: with C-101 full, a member sees "Join waitlist" and the waiting count; selecting it shows a
    pending state, then "On waitlist: 3rd of 3" only after the service confirms; Leave returns the card to
    "Join waitlist". Surface: member client in a real browser/app at 360 px and 1280 px. Confirmed: browser
    journey with controlled response completion (no sleeps).
  - R-8:A2 **F**: server error on join → visible error with Retry, no position shown, control restored;
    `CLASS_FULL`/`NOT_FULL` race responses refresh the card to Join waitlist / Book and say so.
  - R-8:A3 **B**: loading, empty (member has no waitlists), error, and the closed-class card each have a
    designed state; every state is operable by keyboard and its change is announced to assistive technology.
  - R-8:A4 **P**: after R-4:A1 Cai's view shows C-101 as Booked with "promoted from waitlist" without Cai
    taking any action beyond opening/refreshing the app.
- **Open gaps:** G-8 supported client platform(s) and existing identity/design system (needs baseline; the
  NFR-UI rule below is conditional on it).
- **State and data:** the view holds only presentation state and cached reads; the service is authoritative; a
  late response for a superseded request must not overwrite a newer view (latest request wins).

### R-9 Preserved booking behaviour

- **Basis:** the accepted behaviour of the existing app; request 2026-11-21 asks to *add* a waitlist and does not
  mention retiring anything. **Change:** preserve. **Evidence limit:** **no baseline available**: the
  preserved clauses are named but cannot yet be given exact before-values. **Pending:** capture and checks.
- **Behaviour:** these remain exactly as before, and a regression check must pin each against the baseline:
  (a) booking a class with space and an empty waitlist; (b) cancelling a booking and the consequences of
  cancelling that exist today (e.g. late-cancel rules), except that a freed place now goes to R-4; (c) existing
  eligibility rules for booking; (d) existing validation, error behaviour and authorisation of booking and
  cancel; (e) class capacity changes and class cancellation behaviour except as R-4/R-7 add; (f) existing
  data and screens for members with no waitlist.
- **Boundaries/errors:** unchanged. **Consumer outcome:** a member who never touches a full class sees no change.
- **Acceptance**
  - R-9:A1 **P**: characterisation checks captured from the app **before** the change for (a)-(f) still pass
    after it. Confirmed: regression suite at the real service and client.
  - R-9:A2 **F**: a regression that changes any of (a)-(f) fails the suite.
  - R-9:A3 **n/a (boundary)**: boundaries of existing behaviour are inherited from its own checks, which the
    baseline must enumerate (G-0).
- **Open gaps:** **G-0 capture the baseline** of booking, cancel, capacity, eligibility, notification and
  identity behaviour and the stack (owner: discovery of the next run; due before any plan that touches R-4..R-9;
  independent work may proceed on R-1..R-3 only as a model, not as a plan).

### R-10 Waitlist data access and privacy

- **Basis:** request 2026-11-21 (new personal data is introduced: who wants which class); preserved
  privacy/authorisation rules of the existing app. **Change:** add. **Pending:** implementation and checks.
- **Behaviour:** a member can read, create and end only **their own** entries; reads of aggregate waitlist
  count are allowed to any signed-in member; no member can learn another member's identity, entry existence or
  position. Signed-out visitors can do nothing with waitlists (they may see that a class is full, as today).
  Staff visibility of waitlist contents: **not requested**, no staff screen is added (G-10).
- **Boundaries:** an entry stores the member id, class id, order and timestamps only. Logs and notifications
  to other people never contain another member's name or email.
- **Error behaviour:** access to another member's entry → `NOT_ON_WAITLIST`/`NOT_FOUND` with no data revealed
  (same response as a nonexistent entry); unauthenticated → `UNAUTHENTICATED`.
- **Consumer outcome:** a member cannot see who else is waiting; a staff-less deployment still works.
- **Acceptance**
  - R-10:A1 **P**: Cai reads own entry and the count (3); nothing else.
  - R-10:A2 **F**: Fay's request for Cai's entry returns the same answer as for a nonexistent entry; no field of
    any response in R-1/R-2/R-3 contains Dee's or Eli's identity. Confirmed: API-level with different-member tokens
    and a response-body scan.
  - R-10:A3 **F**: signed-out join/leave/read → `UNAUTHENTICATED`.
  - R-10:A4 **B**: log output of a full join→promote→leave sequence contains no names or emails.
    Confirmed: log capture at the real service.
- **Open gaps:** G-10 staff access to waitlists (unresolved, out of scope; owner: product owner).

## Non-functional requirements

Accepted criteria carry ids `NFR-<name>`. Targets not given by the request or the baseline are **unresolved**, not
invented.

- **NFR-conc: integrity under concurrency.** Operating condition: simultaneous joins, leaves, bookings, cancels
  and capacity changes on one class. Criterion: I1-I4 (R-5) hold in every interleaving; checks: the interleavings
  S5 and S6 plus a 10-way concurrent booking/join run (a test workload, not a limit). Surface: the real service
  and store (a mock cannot prove it). Status: planned.
- **NFR-time: promotion timing.** Criterion (observable, not a latency number): promotion has completed by the
  time the operation that opened the place returns (R-4), and class start ends all entries (R-7). A latency
  bound for join/leave/promote is **unresolved** (no baseline latencies, no workload figures); missing evidence:
  current response times and class sizes; owner: product owner/discovery.
- **NFR-capacity: scale.** Waitlist length cap and expected class/member counts: **unresolved** (G-1a). Platform
  quotas of the runtime: **unknown**, must be read from the target before a plan (no stack known).
- **NFR-security.** Authentication required for every waitlist operation; ownership checks on every entry
  (R-10); verified by different-member and signed-out API cases.
- **NFR-privacy.** Entry data = member id + class id + order + timestamps + terminal reason; no personal data in
  logs; terminal-record retention **unresolved** (G-7b); removal of entries on account deletion **unresolved**
  (G-7a).
- **NFR-reliability.** A failed promotion leaves no half-state (R-4:A6); notification failure never undoes a
  booking (R-6:A2). Durability: waitlist entries survive service restarts for as long as they are active (same
  durability as bookings: AD-1).
- **NFR-observability.** Each terminal reason is recorded on the entry (R-7) so "why wasn't I promoted?" is
  answerable without logs; notification failures are recorded (R-6). Verified by reading the records after the
  R-7:A3 and R-6:A2 cases.
- **NFR-compat.** Supported client platforms/browsers: **unresolved** (G-8); a new API/operation must not break
  existing clients that know nothing of waitlists (they must at worst see `CLASS_FULL` as before): verified by
  an existing-client regression run (R-9:A1).
- **NFR-a11y.** Every waitlist control and status meets WCAG 2.2 AA contrast; keyboard operable; visible focus;
  position/status changes announced via an accessible status region; reduced-motion honoured. Verified by
  automated checks plus manual keyboard pass, labelled as such (automation does not prove accessibility).
- **NFR-UI: designed interface.** Applies to the member-facing waitlist surfaces of R-8. Criteria (observable):
  1. one consistent visual system: spacing and type scales as tokens, a palette with **light and dark** themes
     (a new web UI starts light with a dark option);
  2. designed **empty, loading and error** states (R-8:A3), not unstyled placeholders;
  3. layout works at a narrow (360 px) and a wide (1280 px) viewport with **no horizontal overflow** (the two
     widths are verification viewports);
  4. visible focus states and WCAG AA contrast; touch-target size follows the platform's own minimum (no
     number is invented here);
  5. motion only where it explains a change (a position changing, a confirmed promotion), pending/confirmed
     distinguishable, with a reduced-motion alternative; no animation confirms domain success;
  6. one icon set.
  **Visual reference and starting appearance:** *the app already has a UI*, so its established identity and
  platform conventions take precedence and these screens inherit it (G-8 records that the identity is not yet
  seen). Only choices it leaves unspecified use the guide's starting point: the **light Gemini look with
  Material 3 Expressive principles** (`GUIDES/platforms/ui.md#light-expressive-starting-point`): luminous light
  canvas, tonal layered rounded surfaces, friendly precise sans-serif, one restrained saturated accent,
  prominent primary action (Join waitlist/Book), and one visual signature: a clear **position indicator** for
  "2nd of 3". The plan chooses the concrete treatment and records it in an AD. Verified by rendered checks at
  both viewports in both themes, plus keyboard and reduced-motion passes.
- **Exclusions:** no availability/SLA target (not requested; unresolved rather than N/A); no internationalisation
  requirement stated (inherit existing behaviour).

## State, data and service-boundary assessment

State inventory (per piece of state: owner and location · who reads · concurrency · what ends it · quotas):

| State | Owner/location | Readers | Simultaneous changes | Ends/removed | Quotas |
|---|---|---|---|---|---|
| Waitlist entry (class, member, order, status, reason) | Service booking store, same authority and durability as bookings (AD-1) | The member (own); count to any signed-in member | Serialised per class; I1-I4 | R-7 terminal reasons; record retention G-7b | Unknown platform quotas (NFR-capacity) |
| Confirmed booking (existing) | existing | existing | existing + R-5 | existing | existing |
| Client view (position, pending, error) | Member client memory only | that member | latest request wins (R-8) | on navigation; never authoritative | none |
| Notification event (promotion/skip) | existing channel (ASM-5) | the recipient | one per promotion (R-6:A3) | per channel | unknown |

Service boundaries (Service discovery guidance, one line each): **current authority**: the booking service reads
member eligibility at promotion time, never a value cached at join time, so a member who lost eligibility or
access since joining is skipped, not promoted (this is how revocation takes effect without a data edit).
**Freshness vs revocation:** same rule. **Incremental state:** n/a: single store, no replica. **Async completion
and recovery:** the only asynchronous hop is notification, after commit; it never carries state the store
lacks; recovery = booking is the truth, failure recorded (R-6). **Owned event coverage:** terminal reasons and
notification failure are recorded (NFR-observability). No new service, queue or cache is added.

## Retired

none: no earlier spec existed; no requirement is dropped.

## Worked example (replay data)

Fixture: class **C-101** "Spin 6pm", capacity **2**, booked {**Ana**, **Ben**}, waitlist empty, class in the future;
members Cai, Dee, Eli, Fay all signed in and eligible unless stated. Every cancel is by the member named, who is
booked (permitted by ASM-3/R-9); staff actions assume ASM-3. **Status: NOT-REPLAYED**: the reference model that
would recompute these (`scratchpad/model.py`: a rule-checking model, not the product) could not be executed in
this session (execution required an approval that was not granted), so the results below are **hand-derived from
the rules** and remain open until a model or the real service replays them. Hand-checking found one flaw in an
earlier draft (a started class with a non-empty waitlist breaks I1): R-7 now ends entries at start.

| # | Actions in order | Expected (hand-derived) |
|---|---|---|
| S1 | Cai, Dee, Eli join; Cai joins again; Ana joins; Fay books | positions 1,2,3; Cai again → position 1, no duplicate; Ana → `ALREADY_BOOKED`; Fay → `CLASS_FULL`; bookings {Ana, Ben}, waitlist [Cai, Dee, Eli] |
| S2 | (after S1) Ben cancels; Fay books | Cai promoted; bookings {Ana, Cai}, waitlist [Dee, Eli]; Fay → `CLASS_FULL` |
| S3 | (after S2) Dee leaves; Dee leaves again | waitlist [Eli], Eli position 1; second leave → `NOT_ON_WAITLIST` |
| S4 | (after S3) capacity 2→4; Dee joins; Fay books; Dee joins again | Eli promoted, bookings {Ana, Cai, Eli}, waitlist []; Dee's first join → `NOT_FULL` (3 of 4); Fay → `BOOKED` (class full again); Dee's second join → position 1 |
| S5 | cap 1, booked {Ana}, waitlist [Cai]; {Ana cancels, Fay books} in both orders | both orders: bookings {Cai}, Fay `CLASS_FULL`, waitlist [] |
| S6 | cap 2, booked {Ana, Ben}, waitlist [Cai]; Ana and Ben cancel in either order; Fay books | bookings {Cai, Fay}; Cai promoted once |
| S7 | cap 1, booked {Ana}, waitlist [Gus, Hal], Gus ineligible (rule unknown, G-4c); Ana cancels | Gus `ineligible`, Hal promoted, bookings {Hal}, waitlist [] |
| S8 | cap 1, booked {Ana}, waitlist [Cai]; start time passes; Dee joins; Ana cancels (if allowed) | Cai `expired`; Dee `CLASS_CLOSED`; no promotion |
| S9 | waitlist [Cai, Dee, Eli]; Cai leaves, re-joins | [Dee, Eli, Cai], Cai position 3 |

Replay checks the walk (can the actor reach the start, is each action permitted in the state the previous leaves,
can the chosen observer see the result): each join is permitted because the class is full-open (R-1); each
promotion happens inside the cancel that opened the place (R-4); Fay's `CLASS_FULL` follows from I1 (R-5).
S7's ineligibility and any real cancel-after-start behaviour remain unreachable until the baseline names the
rules (G-4c, G-0).

## Open gaps (index; each is recorded under its R)

G-0 baseline capture (R-9) · G-1a waitlist cap, G-1b per-member limit (R-1) · G-2 live updates wanted? (R-2) ·
G-4a claim window vs auto-promotion, G-4b late-cancel/penalty behaviour, G-4c eligibility rules (R-4) · G-5
capacity reduction (R-5) · G-6 notification channel/retry (R-6) · G-7a account deletion, G-7b retention (R-7) ·
G-8 platform and identity (R-8) · G-10 staff access (R-10). **Material conflict:** none found. **Unready work:**
everything depending on G-0 (plan for R-4..R-9); R-1..R-3 and R-5 can be planned against the assumptions once
the owner accepts PD-1..PD-6.

## Submission

- **summary:** Spec for a class-booking waitlist. 10 requirements (R-1..R-10): join a full class's waitlist, FIFO
  order and own-position display, leave, automatic promotion when any place opens (cancel, staff cancel,
  capacity increase), reserved-place and capacity invariants (no queue-jumping, no overbooking under
  concurrency), notifications, entry lifecycle and terminal records, a member-facing UI with designed states,
  preserved booking behaviour, and member-only data access. Status: **open, not ready to plan R-4..R-9**: there
  was no repository, baseline, discovery or research, so existing behaviour is assumption-labelled (ASM-1..6) and
  gap G-0 (capture a baseline) blocks dependent work. **Assumptions/defaults taken unattended:** PD-1 automatic
  promotion without a claim window (owner confirmation open, G-4a); PD-2 FIFO; PD-3 skip-and-remove ineligible
  members; PD-4 re-join at tail; PD-5 own position and count visible; PD-6 entries end at class start; waitlist
  length cap and retention unresolved with interim "no cap / keep". Worked examples S1-S9 are **NOT-REPLAYED**
  (model not executed; results hand-derived). No `backchain-check` here (duty 11 omitted).
- **primary:** R-1, R-4, R-5, R-8 (R-2 and R-6 support outcome B but are not the request's direct ask).
- **evidence_refs:** `KNOWLEDGE/spec.md` (every R-1..R-10 section, NFR section, State/service assessment, worked
  example); `KNOWLEDGE/architecture.md` (AD-1..AD-3); the request text of 2026-11-21 (the only requirements
  source); guides used: `GUIDES/behavioral-requirements.md#behavior-model` and `#traceability-and-review`,
  `GUIDES/requirements-definition.md`, `GUIDES/current-system-baseline.md#planning-and-review-handoff` (no
  baseline existed to reopen), `GUIDES/service-discovery.md#verification`, `GUIDES/project-knowledge.md`,
  `GUIDES/platforms/ui.md#light-expressive-starting-point`. No discovery/research result, repository or earlier
  spec was available; none is cited.
