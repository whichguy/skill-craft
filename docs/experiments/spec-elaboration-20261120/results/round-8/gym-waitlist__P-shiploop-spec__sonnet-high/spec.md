# Class Booking App: Product Specification

Living contract for the class booking app (members book spots in scheduled fitness classes). This run adds
**waitlists for full classes**. Requirements are `R-<n>`; product decisions chosen by default are `PD-<n>`;
open items are `G-<n>`. Structure and technology choices are `AD-<n>` in `architecture.md`, never here.

## Sources, baseline and status

| Item | Status |
| --- | --- |
| Request `REQ-2026-11-21`: "Add a waitlist to our class booking app so full classes don't turn people away." (the user's words, 2026-11-21) | Accepted intent. The only user instruction. |
| Prior spec / `R-<n>` set | None existed in this working directory. Nothing to preserve, change or retire (see `## Retired`). |
| Discovery and research results | None exist. Nothing was run before this stage. |
| Repository / existing app / selected baseline | **Not available.** The booking app's stack, data store, auth, roles, cancellation rules, credits or payments, notification channel and UI platform were not inspected. Recorded as open prerequisite **G-1**. |
| Guides used | `GUIDES/behavioral-requirements.md#behavior-model` and `#traceability-and-review`, `#actors-channels-and-state-ownership`; `requirements-definition.md`; `service-discovery.md#verification`; `platforms/ui.md#light-expressive-starting-point`; `current-system-baseline.md#planning-and-review-handoff`; `project-knowledge.md#maintained-product-requirements`. |
| Working directory | The task names `KNOWLEDGE/` as the working directory, but it does not exist as a subfolder here; the working directory itself holds `GUIDES/`. `spec.md` and `architecture.md` are written at its top level, standing in for `KNOWLEDGE/`. |

**Evidence limit that applies to the whole document.** Everything below is *accepted intent derived from the request
plus labelled default decisions*. No existing behaviour was observed. Wherever a requirement says "preserved", the
preservation is **intent only**; it is unverified until G-1 is closed. Observations: none. Inferences: the existing app
rejects or blocks a booking when a class is full (inferred from the request wording "turn people away"). Unknowns:
everything in G-1.

## Request outcomes and where each is accepted

| Outcome (from `REQ-2026-11-21`) | Acceptance lines |
| --- | --- |
| O-1 A member who wants a full class is not turned away: they can join a waitlist for it | R-1, R-2, R-3, R-10 |
| O-2 The waitlist does its job: when a spot opens the waiting member gets it | R-4, R-5, R-6, R-7 |
| O-3 (implied by "waitlist"; needed for O-1 and O-2 to be trustworthy) fairness, safety and privacy of that list | R-2, R-6, R-8 |
| O-4 (implied) nothing that works today for non-full classes is lost | R-9 |

Out of scope (request leaves them out; also listed under the R they bound): staff-side waitlist management or roster,
paid or priority tiers, claim windows or offer timeouts, waitlist caps, waitlist for recurring series, group or guest
bookings, SMS, any change to pricing or cancellation policy.

## Product decisions (defaults, not user requirements) and assumptions

These fill choices the request leaves open. They are **design/product decisions with rationale, not user
requirements**; a later run must not treat them as user-stated. Each is confirmable via the gap that names it.

| ID | Decision | Rationale | Gap |
| --- | --- | --- | --- |
| PD-1 | Waitlist order is first come, first served by the time the join was accepted. | Simplest rule members can predict; no priority policy was requested. | G-2 |
| PD-2 | Promotion is **automatic**: when a spot opens, the first eligible waitlisted member is booked immediately, no offer to accept. | No timers or claim windows; the "turn away" problem is fixed without more machinery. Trade-off: a member may be booked into a class they no longer want and must cancel under the normal cancellation rules. | G-2 |
| PD-3 | Joining the waitlist is allowed **only while the class is full**. If a spot is free the join is rejected `CLASS_NOT_FULL` and the member is offered a normal booking. | Keeps one path for free spots; makes invariant I-2 hold. | none |
| PD-4 | A member can hold at most one waitlist entry per class, and cannot be both booked and waitlisted for the same class. Waitlisting overlapping classes is allowed. | Overlap rules for bookings are unknown (G-1); waitlisting costs nothing. | G-6 |
| PD-5 | If the head of the waitlist is no longer eligible to book when a spot opens, that entry is removed, the member is told, and the next entry is considered. | Deterministic; the list never holds entries that cannot convert. | G-6 |
| PD-6 | The waitlist closes at class start. Promotion happens up to class start; no earlier cutoff. | No cutoff was requested; inventing one would invent a bound. | G-5 |
| PD-7 | A member sees only their own position and the list length is not shown. | Another person's record stays private; the member needs only their own place. | none |
| PD-8 | Leaving the waitlist asks for confirmation, because rejoining puts the member at the back. | The loss of place is not reversible. | none |
| PD-9 | Joining the waitlist costs nothing and holds no credit or payment; any charge happens only at promotion, exactly as a normal booking would. | Assumes a pay-at-booking model if one exists. | G-6 |
| PD-10 | The "reason" names used below (`CLASS_FULL`, `CLASS_NOT_FULL`, `ALREADY_BOOKED`, `ALREADY_WAITLISTED`, `NOT_ON_WAITLIST`, `NOT_BOOKED`, `CLASS_STARTED`, `NOT_SIGNED_IN`, `NOT_ELIGIBLE`) are logical outcomes. Mapping to the app's existing error convention is a planning decision. | Existing conventions unknown. | G-1 |

## Open gaps

| ID | Gap | Owner | Affects | Effect on readiness |
| --- | --- | --- | --- | --- |
| G-1 | Existing booking app not inspected: stack and data store, transactionality, auth and roles, capacity and cancellation rules (including late-cancel cutoff), credits or payments, overlap rules, time zone and the source of "class start", notification channel, UI platform and identity, existing error convention, existing API consumers. | Discovery or whoever has repository access, before plan | R-1, R-4, R-5, R-9, R-10, NFR-3, NFR-6, NFR-7 | Behaviour-level acceptance lines stand. **Planning and test design for every surface-dependent line stay unready** until baseline is recovered and `## Current-system baseline` below is filled. |
| G-2 | Product owner has not confirmed PD-1 (FIFO) and PD-2 (automatic promotion vs. an offer the member must accept within a window). | Product owner | R-2, R-4 | Defaults are assumed; changing PD-2 changes R-4 and R-5 materially. Work may proceed on the default and must re-check on confirmation. |
| G-3 | Notification channel (email, push, in-app) and wording are unknown. | Product owner and G-1 | R-5 | Only the notification clause of R-5 is unready; the in-app booking state is independent. |
| G-4 | Waitlist cap (per class, per member) unspecified. No bound is invented. | Product owner | R-1, NFR-10 | Treated as unbounded in the spec; capacity planning unready. |
| G-5 | Promotion cutoff before class start (a spot freed 5 minutes before class may be useless to the member). | Product owner | R-4 | Default PD-6; confirm. |
| G-6 | Eligibility rules at join and at promotion (active membership, credits, overlapping booking) and their charge timing. | Product owner and G-1 | R-1, R-4, PD-4, PD-5, PD-9 | If the app has no such rules the clauses are vacuous. Unknown until G-1. |
| G-7 | Whether staff can raise capacity, remove a booking or cancel a class in the existing app. | G-1 | R-4.A6, R-7.A2 | Those acceptance lines are conditional on the capability existing. |
| G-8 | Staff view of a waitlist (names, order) is not requested. | Product owner | R-8 | Left out. |

## Invariants (hold at rest after every operation, in every interleaving)

- **I-1** The booked count of a class never exceeds its capacity because of any booking or promotion.
- **I-2** While a class has not started: a non-empty waitlist implies no free spot (booked ≥ capacity).
- **I-3** A member appears at most once in a class's waitlist and never both booked and waitlisted for that class.
- **I-4** Waitlist order is join order; displayed positions are contiguous from 1.
- **I-5** Once a class has started or been cancelled, its waitlist is empty.

## Requirements

### R-1 Join the waitlist for a full class

- **Basis:** `REQ-2026-11-21`, "full classes don't turn people away". **Change:** add. **Preserved:** booking a class
  that has a free spot is unchanged (R-9). **Changed:** the outcome for a member attempting to book a full class goes
  from rejection to an offer to join the waitlist.
- **Behaviour:** a signed-in, eligible member who is neither booked nor waitlisted for a class that has not started
  yet and is full (booked = capacity) can join its waitlist. The join is accepted by the booking authority, which
  records the member and order, and reports the member's position.
- **Boundaries:** capacity 3 with 3 booked is full; capacity 3 with 2 booked is not (PD-3).
- **Error behaviour:** each rejection changes nothing: `NOT_SIGNED_IN`, `CLASS_NOT_FULL` (free spot; the response
  offers a normal booking), `ALREADY_BOOKED`, `ALREADY_WAITLISTED` (the existing position is reported; no second
  entry), `CLASS_STARTED`, `NOT_ELIGIBLE` (existing booking eligibility, G-6).
- **Consumer outcome:** the member sees "On waitlist, position n" for that class instead of a dead end.
- **Acceptance:**
  - R-1.A1 positive: fixture F-1 (class C-1, capacity 3, booked A, B, C), member D joins, accepted, position 1; E then
    joins, position 2. Surface: member surface and booking authority interface. Confirmed: authority-level test
    against fixture F-1 plus a browser check of the member surface (planned, not run).
  - R-1.A2 failure: in F-1 after D is booked (S-1 step 9), D joins again, rejected `ALREADY_BOOKED`; waitlist and
    bookings unchanged. A member already on the list who joins again gets `ALREADY_WAITLISTED` and keeps position.
    Unauthenticated join gets `NOT_SIGNED_IN`. Same surface and confirmation.
  - R-1.A3 boundary: class C-6 (capacity 2, booked A only), D joins, rejected `CLASS_NOT_FULL`, no entry created;
    the member surface offers Book. Same class after B books (full), D joins, accepted position 1.
  - R-1.A4 boundary: C-3 whose start time has passed, join rejected `CLASS_STARTED`, nothing created.
- **Left out:** waitlist cap (G-4), per-member limit, eligibility policy details (G-6).
- **Pending:** implementation and all checks above. No check has run.

### R-2 Order and position

- **Basis:** `REQ-2026-11-21` (waitlist), PD-1, PD-7. **Change:** add.
- **Behaviour:** the list is ordered by acceptance order (I-4). A member can read their own position at any time. It
  decreases by one when a member ahead of them leaves, is promoted or is removed. Others' identities and the list
  length are not exposed (R-8).
- **Boundaries:** first position is 1; the last joiner has position equal to the entry count.
- **Error behaviour:** position request for a class where the member has no entry returns `NOT_ON_WAITLIST`.
- **Consumer outcome:** the member sees an accurate current position after each reload or own action.
- **Acceptance:**
  - R-2.A1 positive: F-1: D, E, F join, positions 1, 2, 3; E leaves, F's position reads 2 (S-1 step 4); B cancels,
    D is promoted, F's position reads 1 (step 5). Surface: member surface; authority interface. Confirmed: authority
    test plus browser check.
  - R-2.A2 failure: member G with no entry reads position, gets `NOT_ON_WAITLIST`; a different member's position
    cannot be read through G's session (R-8).
  - R-2.A3 boundary: single entry has position 1; after it is promoted no position is shown, the member sees booked.
- **Left out:** priority tiers, manual reordering (G-2).
- **Pending:** implementation and checks.

### R-3 Leave the waitlist

- **Basis:** `REQ-2026-11-21` (waitlist; implied member control), PD-8. **Change:** add.
- **Behaviour:** a member can remove their own entry. Entries behind move up. No booking is affected and nothing is
  charged or refunded. The member surface confirms first (PD-8); cancelling the confirmation leaves the entry and
  position unchanged.
- **Boundaries:** leaving as the only entry leaves an empty list and a still-full class.
- **Error behaviour:** `NOT_ON_WAITLIST` when there is no entry, including when the member was just promoted (the
  response says the member is **booked**, so the interface cannot mislead them into thinking they are off the class).
  A member cannot remove another member's entry (R-8).
- **Consumer outcome:** the member sees "Not on waitlist" and the Join action again.
- **Acceptance:**
  - R-3.A1 positive: S-1 step 4, E leaves, accepted, list D, F, F's position 2.
  - R-3.A2 failure: fixture S-2b (capacity 1, booked A, waitlist D, F), A cancels and D leaves concurrently: in the
    order cancel then leave, D's leave returns `NOT_ON_WAITLIST` and D is booked, F is position 1; in the order leave
    then cancel, D's leave succeeds and F is promoted. Either result is acceptable, no other is.
  - R-3.A3 boundary: dismissing the confirmation leaves D at position 1 unchanged.
- **Left out:** bulk removal, staff removal (G-8).
- **Pending:** implementation and checks.

### R-4 Automatic promotion when a spot opens

- **Basis:** `REQ-2026-11-21`, "full classes don't turn people away"; PD-2, PD-5, PD-6. **Change:** add. **Preserved:**
  a cancellation continues to free the member's spot exactly as today (G-1).
- **Behaviour:** when a spot in a not-yet-started class opens (a member cancels; or capacity rises, or staff remove a
  booking, if those exist, G-7) and the waitlist is non-empty, in the same atomic operation the first eligible entry
  is removed from the waitlist and booked (I-2, AD-1). One spot promotes exactly one member. k spots promote the first
  k eligible entries in order. If the head is ineligible (PD-5) it is removed, the member is told, and the next is
  tried. If the waitlist is empty the spot simply becomes available for normal booking.
- **Boundaries:** a spot opening after class start promotes nobody (PD-6, G-5).
- **Error behaviour:** if the promotion cannot be written, the cancellation also does not take effect and the
  canceller sees an error (AD-1); I-2 is never left broken at rest.
- **Consumer outcome:** the waiting member finds themselves booked, without acting.
- **Acceptance:**
  - R-4.A1 positive: F-1 steps 1-5. B cancels with waitlist D, F: booked A, C, D, waitlist F. Then steps 7-8 end with
    booked D, F, E and an empty waitlist. Surface: booking authority interface and the promoted member's bookings
    view. Confirmed: authority-level test, then member-surface check.
  - R-4.A2 failure: S-3 (capacity 1, booked A, waitlist D ineligible, E): A cancels; D is removed with a
    notification, E is booked. Conditional on G-6 defining ineligibility.
  - R-4.A3 failure: a write failure injected at the promotion step leaves A still booked and the waitlist
    unchanged, and the cancel call fails.
  - R-4.A4 boundary: S-6 (capacity 2, booked A, B, empty waitlist): A cancels, nobody is promoted, one spot is free,
    a direct booking by D then succeeds.
  - R-4.A5 boundary: a spot freed after class start (S-5) promotes nobody; the waitlist is already empty (I-5).
  - R-4.A6 boundary, conditional on G-7: S-4, capacity 3 raised to 5, booked A, B, C, waitlist D, E, F, G: D and E
    are promoted, waitlist F, G, booked 5 (I-2 holds as booked = capacity).
- **Left out:** claim windows or offers (G-2), earlier promotion cutoff (G-5), refunds.
- **Pending:** implementation and checks; confirmation of PD-2 (G-2).

### R-5 Promotion is visible and the member is told

- **Basis:** `REQ-2026-11-21` (waitlist is only useful if the member learns of the outcome), PD-2. **Change:** add.
- **Behaviour:** after a promotion, the class appears in the member's bookings, authoritative on its own. A
  notification is attempted through the channel chosen under G-3 stating class, date and time. Notification is
  best-effort and sent after the promotion commits; a delivery failure never undoes the booking and is recorded
  (NFR-8). Removal under PD-5 or class cancellation (R-7) also notifies.
- **Boundaries:** one notification per promotion even if the triggering request is retried (idempotent).
- **Error behaviour:** failed delivery leaves the booking in place.
- **Consumer outcome:** the member learns they are booked either by notification or on next view of their bookings.
- **Acceptance:**
  - R-5.A1 positive: S-1 step 5: D appears in D's bookings for C-1 and exactly one notification record exists for D.
  - R-5.A2 failure: the notification sink fails at step 5: D is still booked, a delivery-failure event is logged,
    no second booking exists.
  - R-5.A3 boundary: the cancel request is retried with the same identity after step 5; D is not promoted twice and
    gets one notification.
  - Surface: authority interface, bookings view, sink observed through the existing channel or a test double (G-3).
- **Left out:** channel selection, copy (G-3).
- **Pending:** implementation and checks; G-3.

### R-6 Consistency under concurrent changes

- **Basis:** `REQ-2026-11-21` (a waitlist that mis-assigns spots turns people away anyway), I-1 to I-5. **Change:**
  add.
- **Behaviour:** simultaneous joins, leaves, bookings and cancellations resolve as if executed in some serial order;
  the outcome equals one of those serial orders' outcomes. A freed spot goes to the head of the waitlist, never to a
  direct booker (a direct booking of a full class is `CLASS_FULL`, which offers the waitlist). No member is promoted
  twice and no spot is double-assigned.
- **Error behaviour:** the loser of a race gets the reason that matches the serial order in which it lost.
- **Consumer outcome:** every member's screen, after refresh, agrees with the authority.
- **Acceptance:**
  - R-6.A1 positive: S-2 (capacity 1, booked A; three actions: A cancels, D joins, E books directly): each of the six
    serial orders gives the outcome in the S-2 table; a concurrent run's observed outcome must equal one of the six.
  - R-6.A2 failure: after any run of mixed operations I-1 to I-5 hold; a sample of 20 simultaneous requests on one
    class (verification input, not a product bound) never violates them.
  - R-6.A3 boundary: capacity 1 with one free spot and D, E both booking directly: exactly one succeeds, the other
    gets `CLASS_FULL`.
  - Surface: authority interface under concurrent calls; confirmed by an automated concurrency test, not by UI.
- **Left out:** fairness across multiple instances of the authority (depends on G-1/AD-1).
- **Pending:** implementation and checks.

### R-7 Waitlist lifecycle ends cleanly

- **Basis:** `REQ-2026-11-21` (waitlist), I-5, PD-6. **Change:** add.
- **Behaviour:** at class start the waitlist is closed and its entries removed; members still waitlisted are not
  booked and are told the class started without a spot. If the class is cancelled (existing staff action, G-7), all
  entries are removed and members notified together with booked members as today. If a member's account is deleted
  or deactivated their entries are removed (if the app supports it, G-1).
- **Boundaries:** at the exact start instant the class counts as started (`CLASS_STARTED`); the start source and
  time zone come from the existing app (G-1).
- **Error behaviour:** joining after start is `CLASS_STARTED`.
- **Consumer outcome:** no stale "on waitlist" shows for a class that has begun.
- **Acceptance:**
  - R-7.A1 positive: S-5, class C-3 with waitlist D, E: at start the waitlist is empty, D and E see "waitlist
    closed", nobody is booked beyond capacity.
  - R-7.A2 failure (conditional on G-7): class cancelled with waitlist D: D's entry is removed and D notified.
  - R-7.A3 boundary: at the start instant join returns `CLASS_STARTED`. Needs a controllable clock (NFR-9).
- **Left out:** retaining history of waitlist entries beyond class start.
- **Pending:** implementation and checks.

### R-8 Access and privacy

- **Basis:** the information-lifecycle duty; `REQ-2026-11-21` adds personal data to a new record. **Change:** add.
- **Behaviour:** a member can read, create and remove only their own waitlist entry for any class. A member never
  receives another member's identity, the other entries or the total length (PD-7). The authority derives the actor
  from the session, never from a member id supplied by the client.
- **Error behaviour:** attempts on another member's entry are rejected without revealing whether it exists.
- **Consumer outcome:** nobody can learn who else is waiting.
- **Acceptance:**
  - R-8.A1 positive: D reads own entry, position 1.
  - R-8.A2 failure: session of E submits a leave carrying D's member id; the request acts only on E's own entry
    (`NOT_ON_WAITLIST` for E) and D's entry is unchanged. Responses for the class never contain other members' ids
    or the list length.
  - R-8.A3 boundary: a class with no entries returns the same shape as a class where the member has none.
  - Surface: authority interface responses, inspected directly, and the member surface payload.
- **Left out:** staff views (G-8).
- **Pending:** implementation and checks.

### R-9 Booking behaviour that does not involve a full class is preserved

- **Basis:** the user's silence on other behaviour preserves it (requirements-definition: silence is not retirement);
  `REQ-2026-11-21` asks only for waitlist behaviour. **Change:** preserve (intent), modify one clause: a booking attempt
  on a full class now ends in `CLASS_FULL` with a waitlist offer.
- **Behaviour:** booking a class with a free spot, cancelling a booking, listing classes and the capacity limit work
  as they do today. Capacity is never exceeded (I-1).
- **Error behaviour:** every existing rejection reason for non-full classes (G-1) is unchanged.
- **Consumer outcome:** existing members see no change except the offer on full classes.
- **Acceptance:**
  - R-9.A1 positive: C-6 with a free spot, D books, accepted exactly as before.
  - R-9.A2 failure: B cancels a booking they do not hold: `NOT_BOOKED`, nothing changes.
  - R-9.A3 boundary: a client that does not know about waitlists receives the existing full-class rejection (not a
    new shape that breaks it), if such clients exist (G-1).
  - Confirmed by: regression suite of the existing app, once G-1 yields it. **Cannot be written until G-1 is closed.**
- **Pending:** G-1 and checks.

### R-10 Waitlist behaviour on the member surface

- **Basis:** `REQ-2026-11-21`; UI-delivery duty. **Change:** add.
- **Behaviour:** on a full class the primary action reads "Join waitlist" (replacing a disabled "Class full"). After
  joining it shows "On waitlist, position n" with "Leave waitlist". After promotion it shows booked. Feedback is
  truthful: a pending state ("Joining...", the action disabled to prevent double submit) lasts until the authority
  answers; the position appears only from the authority's response, never optimistically; on rejection the specific
  reason is shown inline with a way to retry or to take the proper alternative (Book when `CLASS_NOT_FULL`). The
  surface re-reads authoritative state on load, on regaining focus and after each own action; no push is required.
  Another member's action may make the display stale until then; any action taken on stale state is re-validated by
  the authority and the response reconciles the display.
- **Error behaviour:** a network failure shows a persistent error with retry, not a transient toast alone. Unknown
  outcome after a lost response is resolved by re-reading state before offering retry.
- **Consumer outcome:** the member always knows whether they are booked, waitlisted or neither, and why an action failed.
- **Acceptance:**
  - R-10.A1 positive: member D on C-1 views a full class, taps Join waitlist, sees pending, then "position 1".
  - R-10.A2 failure: join answered `CLASS_NOT_FULL`: inline message and a Book action; no phantom position is shown.
    Server unreachable: persistent error with retry, no position displayed.
  - R-10.A3 boundary: double activation of Join sends one request (disabled during pending); a response arriving
    after the member navigated away does not overwrite newer state for another class.
  - Surface: member surface on the app's actual UI platform (G-1), browser or device check; confirmed with
    controlled response timing. A screenshot alone does not confirm A3.
- **Left out:** live push of position changes.
- **Pending:** G-1 for the platform; implementation and checks.

## Retired

None. No prior requirements existed.

## Current-system baseline

*Empty: G-1.* To be filled with observed behaviour of the booking app (separately from intent) before planning. The
sections R-1, R-4, R-5, R-9, R-10 must be mapped to it as preserve/modify decisions.

## Non-functional requirements

| ID | Quality | Requirement, bound or criterion | Operating conditions | Verification | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-1 | Integrity / consistency | I-1 to I-5 hold in every interleaving (R-6). Observable: no capacity overrun, no double booking, no duplicate entry. | concurrent requests against one class | concurrency test at the authority interface | accepted; unverified |
| NFR-2 | Durability, reliability | Waitlist entries and promotions survive restart of the app/service, in the same durable store as bookings. | process restart | restart, then read state | accepted; unverified; store unknown (G-1) |
| NFR-3 | Performance, capacity | **Unresolved.** No latency, throughput or workload figures exist; none are invented. Missing evidence: current load and any existing target (G-1). Owner product owner; due at test-strategy. | n/a | n/a | unresolved |
| NFR-4 | Security and privacy | R-8. The only personal datum added is the member id on an entry. It is shown only to its owner, never logged beyond the id, removed at class start, class cancel or account removal (R-7). | | inspect responses and logs | accepted; unverified |
| NFR-5 | Accessibility | WCAG 2.2 AA is the target for the waitlist surfaces (text contrast 4.5:1, interface component contrast 3:1), operable by keyboard, status changes ("position 2", "you are booked") announced to assistive technology, accessible names on all actions. | the app's UI platform | automated audit plus keyboard walkthrough | accepted; unverified |
| NFR-6 | UI quality | See below. | | browser check at 320 and 1280 px | accepted; unverified |
| NFR-7 | Compatibility | Existing API consumers and clients keep working (R-9.A3); degradation for clients unaware of waitlists is the existing full-class rejection. | | contract/regression test | unresolved until G-1 |
| NFR-8 | Observability | The authority records events with class id, member id, reason and order: `waitlist.joined`, `waitlist.left`, `waitlist.promoted`, `waitlist.removed`, `notification.failed`. No other personal data. | | assert events in a test sink | accepted; unverified; sink unknown |
| NFR-9 | Testability | The authority's notion of "now" is controllable, so class start, the start instant and cutoff behaviour are testable without waiting (R-7.A3). | | test-time clock | accepted |
| NFR-10 | Scale of the list | **Unresolved** (G-4): no cap given; none invented. | | | unresolved |

Exclusions with reasons: SLA or availability target (no service level exists in the request or any evidence; part of
NFR-3, unresolved, not N/A); internationalisation (no evidence the app has locales, G-1).

### NFR-6 Designed interface for waitlist surfaces

**Visual direction.** A new screen inside an existing product inherits its identity. The app's identity is unknown
(G-1), so: where the app has an established identity, use its tokens; for choices it leaves unspecified, use the
**light expressive starting point** (`platforms/ui.md`): the light Google Gemini look and feel with Material 3
Expressive principles, adapted to the app's own name and content. Starting appearance: **light, with a dark option**,
unless an established appearance policy says otherwise. The plan chooses concrete tokens and records them in the
architecture decisions for the UI. The strongest visual weight goes to the member's primary activity: the join
action and the position status on the class.

Observable criteria:
1. One visual system: spacing and type scales, a palette with light and dark themes; no one-off values.
2. Designed empty ("nobody ahead of you" is not shown; no list length), loading ("Joining..."), error (persistent
   inline with retry) and success (position, booked) states.
3. Layout works at 320 px and 1280 px wide with no horizontal overflow.
4. Visible keyboard focus on every control; WCAG AA contrast in both themes.
5. Motion only to explain a change (position change, promotion), honouring `prefers-reduced-motion` with a static
   alternative; no replay of a stale success animation after resume.
6. One icon set.

## State and data assessment

| Resource | Owner and location | Change | Identity | Before / after invariant | Recovery | Check |
| --- | --- | --- | --- | --- | --- | --- |
| Waitlist entry (class, member, join order, status) | Booking authority; same durable store as bookings (G-1, AD-1) | created on join; deleted on leave, promotion, removal, class start/cancel | (class id, member id) | I-2 to I-4 before and after each operation | promotion and cancel are one atomic unit; if the store cannot give atomicity, a repair that promotes whenever booked < capacity and the list is non-empty must exist and be idempotent (AD-1) | R-4.A3, R-6.A2 |
| Booking (existing) | Booking authority | created by direct booking or promotion; deleted by cancel | (class id, member id) | I-1 | as above | R-4.A1, R-9 |
| Class capacity and start (existing) | Existing app; read only here, except G-7 | observed; capacity change only if G-7 | class id | I-1 | n/a | R-4.A6 |
| Notification record | Authority or the notification channel (G-3) | created after commit | promotion id | at most one per promotion | retry safe; failure never rolls back | R-5 |
| Member-surface display state (position, pending) | the client, transient | derived | n/a | never authoritative | re-read from authority | R-10 |

Unknowns: transaction support (G-1), idempotency key for retried cancels (G-1), where start time is stored (G-1).
Migration: waitlist entries are a new record; no existing record is migrated. Staged release: no containment is
claimed (platform unknown); rollback limit is that removing the feature drops waitlist entries, and any member
promoted by it keeps their booking.

## Service boundary contracts

Boundary: member surface to the booking authority. Not a new service.

- Current authority: the booking authority alone decides capacity, order and promotion. The client holds no
  authoritative waitlist state.
- Freshness versus revocation: the client may show data fetched at load; it re-reads on focus and after own actions.
  Loss of a place (promotion, removal, class start) is discovered at the next read; actions are re-validated.
- Incremental state: n/a, whole-entry reads; no cursor.
- Async completion and recovery: join, leave and cancel complete synchronously, including promotion. Notification
  is the only async part: best-effort after commit, delivery failure recorded, no queue added (AD-2). An unknown
  outcome after a lost response is resolved by re-reading state.
- Owned event coverage: NFR-8 events; provider login coverage n/a.
- Inapplicable: caching beyond the client's display, subscriptions and push, cross-service durable work.

## State and information lifecycle

| State | Owner, location | Who reads | Simultaneous changes | Ends / removed | Quotas |
| --- | --- | --- | --- | --- | --- |
| Waitlist entry | authority, durable store | its member only (R-8); the authority | serial order (R-6) | leave, promotion, PD-5 removal, class start or cancel, account removal | unknown (G-1, G-4) |
| Pending / position display | client memory | the member | latest authoritative response wins; superseded responses are discarded | on navigation or reload | none |
| Notification | channel (G-3) | the member | idempotent per promotion | channel policy | unknown (G-3) |

Personal data: the member id on a waitlist entry. Shown only to its member; stored in the booking store; logged only
as an id in NFR-8 events; kept until the entry ends; removed with the entry. No identity, sharing or persistence beyond
the above is added.

UI premises (affected UI only): **components**: class card action ("Join waitlist" / "Leave waitlist"), status chip
("On waitlist, position n"), inline reason message, leave-confirmation dialog; each with default, pending, error,
disabled and focus states. **Interaction**: R-10; the screen works with the server absent (shows a persistent error, no
invented state). **Skin**: NFR-6.

## Flows and transitions (compact ledger)

Flows: F-1 join (R-1, R-2, R-10), F-2 leave (R-3, R-10), F-3 cancel and promote (R-4, R-5, R-6), F-4 class start or
cancel (R-7), F-5 direct booking (R-6, R-9).

| T | Event and guard | Before to after | Rejection and effects | Cases |
| --- | --- | --- | --- | --- |
| T-1 | join, member not booked or waitlisted, class not started and full | not listed to waitlisted at position n+1 | otherwise a reason from R-1, no change | R-1.A1-A4 |
| T-2 | leave, member waitlisted | waitlisted to not listed, followers move up | `NOT_ON_WAITLIST`, no change | R-3.A1-A3 |
| T-3 | cancel by a booked member, class not started | booked to not booked; waitlist head promoted, if any (T-4) | `NOT_BOOKED`, `CLASS_STARTED`, no change | R-4.A1, A4, A5 |
| T-4 | spot free and list non-empty (inside T-3, or capacity raised) | head waitlisted to booked; ineligible head to removed and told (PD-5) | on write failure the whole of T-3 is undone | R-4.A2, A3, A6 |
| T-5 | direct book | not booked to booked if free | `CLASS_FULL` offers waitlist; `ALREADY_BOOKED`; `ALREADY_WAITLISTED` | R-6.A3, R-9.A1 |
| T-6 | class start or cancel | waitlisted to removed | none; join gives `CLASS_STARTED` | R-7 |

Event families audited: duplicates and retries (R-1.A2, R-5.A3), invalid actor (R-8), concurrency (R-6), partial
failure (R-4.A3, R-5.A2), expiry (R-7), boundary (R-1.A3, R-4.A4). Left out: timeouts and claim windows (G-2).

## Replay fixtures and walks

Fixture F-1: class C-1, capacity 3, starts 2026-12-01 18:00 studio-local (future relative to 2026-11-21), booked A,
B, C, waitlist empty; D, E, F signed in, eligible, no bookings. Cancellation is assumed allowed ten days before start
(late-cancel rule unknown, G-1).

**S-1** (hand-walked; the rule that permits each deciding action is named):

| # | Action | Permitted by | Result | booked / waitlist after |
| --- | --- | --- | --- | --- |
| 1 | D join | R-1 (full, 3 of 3) | accepted, position 1 | A B C / D |
| 2 | E join | R-1 | position 2 | A B C / D E |
| 3 | F join | R-1 | position 3 | A B C / D E F |
| 4 | E leave | R-3 | accepted; F position 2 | A B C / D F |
| 5 | B cancel | existing cancel; R-4 | accepted; D promoted; F position 1 | A C D / F |
| 6 | E book directly | R-6 | `CLASS_FULL`; then E join accepted, position 2 | A C D / F E |
| 7 | A cancel | R-4 | F promoted | C D F / E |
| 8 | C cancel | R-4 | E promoted | D F E / (empty) |
| 9 | D join | R-1 | `ALREADY_BOOKED`, no change | D F E / (empty) |

**S-2** (capacity 1, booked A, waitlist empty; actions cancelA, joinD, bookE; all six serial orders, hand-walked):

| Order | Results | booked / waitlist |
| --- | --- | --- |
| cancelA, joinD, bookE | ok, `CLASS_NOT_FULL`, ok | E / none |
| cancelA, bookE, joinD | ok, ok, joinD position 1 | E / D |
| joinD, cancelA, bookE | position 1, ok (D promoted), `CLASS_FULL` | D / none |
| joinD, bookE, cancelA | position 1, `CLASS_FULL`, ok (D promoted) | D / none |
| bookE, cancelA, joinD | `CLASS_FULL`, ok, `CLASS_NOT_FULL` | none / none |
| bookE, joinD, cancelA | `CLASS_FULL`, position 1, ok (D promoted) | D / none |

Fifth order ends with a free spot and both D and E rejected for correct reasons; each can book directly next.
**S-2b** (capacity 1, booked A, waitlist D F): cancelA then leaveD gives D booked, F waitlisted position 1, D's leave
`NOT_ON_WAITLIST`; leaveD then cancelA gives F booked, empty waitlist. **S-3**: capacity 1, booked A, waitlist D
(ineligible), E: A cancels, D removed and told, E booked, waitlist empty. **S-4**: 3 to 5, booked A B C, waitlist D E F G:
D, E promoted, waitlist F G. **S-5**: class C-3 starts with waitlist D, E: waitlist empty, join `CLASS_STARTED`.
**S-6**: capacity 2, booked A B, empty list: A cancels, B only booked, no promotion.

**Replay status: NOT-REPLAYED.** A guarded model of these rules was written at `.tmp/walk.py` (every action checks its
guard; it asserts I-1 to I-5 over S-1 to S-6 and 3000 random operation sequences), but running Python was not
approved in this environment, so it **has not executed**; no execution is claimed. The tables above are by hand, and
are therefore stale-if-rules-change and unconfirmed by machine. Closing this: run `python3 -I .tmp/walk.py` and compare
its output with the tables. An unreachable-start check: all fixtures start from states reachable under R-1 and R-4
(each waitlisted member joined a full class; each promoted member was ahead in order). S-4 and the cancel steps
depend on G-7 and the unknown cancel cutoff (G-1).

## Traceability

R-1: O-1 | R-2: O-1, O-3 | R-3: O-1 | R-4: O-2 | R-5: O-2 | R-6: O-2, O-3 | R-7: O-2 | R-8: O-3 | R-9: O-4 | R-10: O-1.
Every outcome O-1 to O-4 has at least one acceptance line above. Primary outcomes (asked directly): R-1, R-2, R-4.

## Submission

- **summary:** Spec for a waitlist on a class booking app, from the request "Add a waitlist to our class booking app
  so full classes don't turn people away." Ten requirements R-1 to R-10 (join, order and position, leave, automatic
  promotion, promotion visibility and notice, concurrency consistency, lifecycle end, privacy, preserved booking
  behaviour, member-surface behaviour), five invariants, ten NFRs (two unresolved, see below), a state and data
  assessment and replay fixtures S-1 to S-6. **Open (blocking only dependent work):** G-1, the existing app was not
  available, so no baseline, stack, surface or existing rules were observed; planning and tests for R-1, R-4, R-5,
  R-9, R-10 and NFR-6, NFR-7 stay unready until recovered, while the behaviour-level lines stand. Product defaults
  needing owner confirmation: PD-1 first come first served and PD-2 automatic promotion (G-2); also G-3 channel, G-4
  cap, G-5 cutoff, G-6 eligibility, G-7 staff capabilities. NFR-3 (performance) and NFR-10 (cap) are unresolved by
  design; no bound was invented. No material requirement conflict. Replays are `NOT-REPLAYED`: the guarded model
  script was not run (execution not approved); scenario results are by hand. Duty 11 omitted as instructed. Assumptions
  recorded: PD-1 to PD-10. `KNOWLEDGE/` did not exist, so files sit in the working directory.
- **primary:** R-1, R-2, R-4
- **evidence_refs:** `spec.md` (all requirement sections R-1 to R-10, NFR, state and data, service boundary, lifecycle,
  fixtures); `architecture.md` (AD-1, AD-2, AD-3); request `REQ-2026-11-21`; guides listed under "Sources";
  `.tmp/walk.py` (not executed).
