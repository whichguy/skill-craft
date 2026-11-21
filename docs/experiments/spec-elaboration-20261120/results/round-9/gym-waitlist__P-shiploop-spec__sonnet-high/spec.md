# Class Booking App: Product Requirements

Living product specification. Requirement IDs are `R-<n>` only. Product decisions taken as
defaults are `PD-<n>`; open items are `G-<n>`. Structure and technology choices are `AD-<n>` in
`KNOWLEDGE/architecture.md`, never here.

## Status and baseline

- Run kind: first spec for this product in this harness. No prior `spec.md`, no research or discovery
  result, no repository and no selected baseline were available. **Evidence limit:** nothing below was
  checked against the real app. Every statement about "existing" booking behaviour is an assumption,
  listed in G-1, not an observation.
- Request (source S-1, 2026-11-21): "Add a waitlist to our class booking app so full classes don't turn
  people away."
- Accepted earlier requirements: none. Retired: none (see `## Retired`).
- Terms. *Member*: a signed-in person who books classes. *Class*: one scheduled session with a capacity,
  a start time and a status. *Booking*: a member's confirmed seat in a class. *Full*: confirmed bookings
  equal capacity. *Waitlist entry*: a member's place in line for one full class.

## Product decisions and assumptions (defaults taken unattended)

| ID | Default | Why it is a default |
| --- | --- | --- |
| PD-1 | Queue order is first come, first served by join order, per class. | The request names no priority rule. |
| PD-2 | A freed seat is given to the first eligible entry automatically and at once; there is no claim window or confirm step. | No timer or offer state is needed, so there is nothing to expire. Reverse this if booking costs money or credits at booking time (G-2). |
| PD-3 | The waitlist is open only while normal booking for that class is open. Where the app has no separate cutoff, that is until the class start time. After that no promotion occurs. | Promoting someone into a class that has begun helps nobody. |
| PD-4 | A member may hold at most one active entry per class, and cannot hold an entry while holding a booking in that class. | Avoids duplicate seats. |
| PD-5 | A direct "book" on a full class, or on a class whose waitlist is non-empty, is refused with `class_full`. It never takes a seat ahead of the queue. | Fairness: the waitlist would be pointless if walk-up booking could skip it. |
| PD-6 | A member sees only their own entry and position, never other members' identities. | Privacy default; the request needs no more. |
| PD-7 | Waitlist entry records are kept, with a final status, for as long as booking records are kept. | No retention period is given; none is invented (G-5). |
| PD-8 | No cap on waitlist length is enforced. | Request names none (G-4). |
| PD-9 | Staff roster views, manual reordering and staff removal are out of scope. | Not requested (G-6). |

## Request outcomes

| Outcome | Wording in S-1 | Covered by |
| --- | --- | --- |
| O-1 | "Add a waitlist": a member can queue for a class. | R-1, R-2, R-3, R-7 |
| O-2 | "full classes don't turn people away": a member who meets a full class is offered a place in line, and gets the seat when one opens. | R-1, R-4, R-5, R-8 |

## Requirements

Each acceptance line reads: expectation; **Surface** where observed; **Confirm** how it is checked. The
fixture used by the examples is defined once here.

**Fixture F** (used by the replayable examples): class `C1`, "Spin", capacity 2, start time T0+48h (T0 is
the test start), status scheduled. Members Ana, Ben, Cara, Dev, Eli, Fay: all signed in, active and eligible
under the app's normal booking rules. Ana and Ben hold bookings in C1 unless a step says otherwise. Every
cancellation in an example happens before the class starts and is one the existing app already permits (G-1).

### R-1 Join the waitlist for a full class (primary)

Behaviour: a signed-in member who views a full, open class is offered "Join waitlist" in place of the
turned-away state. Joining creates an active entry at the end of that class's queue and shows the member
their position.
Boundaries: the class must be full, open (PD-3), and the member must hold no booking in it (PD-4).
Error behaviour: a rejected join leaves the queue and bookings unchanged and states the reason.
Consumer outcome: the member sees "On the waitlist, #n" for that class.

- AC-1.1 Positive: with Fixture F, Cara joins C1 and gets position 1; then Dev gets 2 and Eli gets 3.
  Surface: member UI class card and the booking service response. Confirm: UI end-to-end test; service
  contract test.
- AC-1.2 Failure: a join by a signed-out caller is refused (`not_authenticated`) and creates nothing.
  Surface: booking service interface. Confirm: service contract test.
- AC-1.3 Boundary: n/a: join rejections on closed, booked or not-full classes are R-2; duplicates are R-10.

### R-2 Join is refused where a waitlist makes no sense

Behaviour: join is refused, with a distinct reason code, when the class is not full (`class_not_full`), the
member already holds a booking in it (`already_booked`), or the class is cancelled or has started
(`class_closed`).
Boundaries: "not full" means confirmed bookings < capacity *and* the waitlist is empty (PD-5); with a
non-empty queue the class counts as full for joining.
Error behaviour: state unchanged. For `class_not_full` the UI refreshes the class card to the normal "Book"
action, so a member who raced a freed seat is not stranded (join never silently books).
Consumer outcome: an actionable message per code.

- AC-2.1 Positive: n/a: the successful join is AC-1.1.
- AC-2.2 Failure: with an empty non-full class (C1 with no bookings), Fay's join returns `class_not_full`
  and no entry exists; Ana, who holds a booking in a full C1, gets `already_booked`; joining C1 once it is
  cancelled returns `class_closed`. Surface: booking service interface; UI message. Confirm: service
  contract test; UI test for the message and the refresh to "Book".
- AC-2.3 Boundary: a join at exactly the class start time (T0+48h) is `class_closed`; one a minute earlier
  succeeds. Surface: service. Confirm: contract test with a controllable clock.

### R-3 Members see their own waitlist status (primary)

Behaviour: the member sees, per class, whether they are on the waitlist and their 1-based position, and a
"Waitlisted" list in their bookings area. Position is derived from the live queue, so it drops as people
ahead leave or are promoted.
Boundaries: only the member's own entries (PD-6). Position is never shown for another member.
Error behaviour: if status cannot be loaded, the UI shows an error with retry, never a stale "#n" as if
current.
Consumer outcome: after Ben cancels in Fixture F (see AC-4.1), Dev's view changes from #2 to #1 and Eli's
from #3 to #2 on next load or refresh.

- AC-3.1 Positive: as in the consumer outcome. Surface: member UI; status read of the service. Confirm: UI
  end-to-end; service contract.
- AC-3.2 Failure: Dev requests Cara's entry status and is refused (`forbidden`), disclosing neither
  existence nor position. Surface: service. Confirm: contract test with two members.
- AC-3.3 Boundary: a member with no entry gets an empty result, not an error. Surface: service and UI empty
  state. Confirm: contract test; UI test.

### R-4 A freed seat goes to the first waitlisted member automatically (primary)

Behaviour: when a seat in a full class is freed, the first active entry whose member is eligible (R-6)
becomes a confirmed booking in the same operation as the freeing, and the entry ends as `promoted`.
Triggers: the member's own booking cancelled; staff cancelling a booking, where the app has that action;
capacity increased, where the app lets staff edit it (one seat per added unit, in queue order). If the app
has none of the staff triggers they simply do not exist; they are not added (G-1).
Boundaries: no promotion at or after class start (PD-3) or for a cancelled class. A freed seat with no
eligible entry leaves the class open for normal booking.
Error behaviour: if promotion cannot complete, the cancellation that freed the seat is not left half done:
either both happen or neither (see R-10).
Consumer outcome: the promoted member sees the booking in their bookings with its origin ("from waitlist")
and receives the notice of R-8.

- AC-4.1 Positive (replayable, Example E-1): Fixture F; Ana and Ben booked; Cara, Dev, Eli join in that
  order (1, 2, 3). Ben cancels. Expected: C1 bookings are Ana and Cara; waitlist is Dev #1, Eli #2; Cara's
  entry is `promoted`. Surface: member UI of Cara, Dev and Eli; service reads. Confirm: end-to-end test
  using three sessions.
- AC-4.2 Failure: n/a: an unauthorised cancel is existing behaviour (R-11) and frees no seat.
- AC-4.3 Boundary (Example E-8): Ben's cancellation lands at exactly T0+48h with Eli waiting. Expected:
  no promotion; C1 bookings are Ana only, Eli's entry reads as ended `class_started`, and the class is not
  open for booking. Surface: service reads. Confirm: contract test with a controllable clock.
- AC-4.4 Boundary: where staff may raise capacity from 2 to 4 with Cara, Dev, Eli waiting, Cara and Dev are
  promoted in that order and Eli becomes #1. Surface: service. Confirm: contract test. Applies only if the
  capacity-edit capability exists (G-1).

### R-5 Queue order is fair and cannot be jumped (primary)

Behaviour: promotion order is join order (PD-1). A direct booking attempt on a full class, or on a class
with a non-empty waitlist, is refused with `class_full` and the UI offers the waitlist (PD-5). A member who
leaves and rejoins goes to the back.
Boundaries: the ordering key is assigned by the service, not the client, so client clocks cannot change it.
Error behaviour: refused booking changes nothing.
Consumer outcome: nobody who joined later is seated before somebody who joined earlier.

- AC-5.1 Positive: Example E-5: Ana and Ben booked, Cara waiting. Fay's booking attempt is refused with
  `class_full`. Ben cancels; Cara is promoted; Fay's retry is again `class_full`. Surface: service and UI
  "Join waitlist" offer. Confirm: contract test; UI test.
- AC-5.2 Failure: n/a: the refusal itself is the positive case here.
- AC-5.3 Boundary: Cara leaves and rejoins behind Dev and Eli; she is then #3. Surface: service. Confirm:
  contract test.

### R-6 Promotion re-checks eligibility and skips the ineligible

Behaviour: at promotion time the member must still satisfy the same conditions the app applies to a normal
booking at that moment (for example the account is active). An ineligible first entry is ended as
`skipped_ineligible` and the next entry is tried, until a seat is filled or the queue is empty.
Boundaries: the rule set is the app's own; this spec adds none (G-1).
Error behaviour: a skipped member is notified (R-8) and keeps no seat; later entries keep their order.
Consumer outcome: a seat is never wasted on someone who cannot take it while someone behind them can.

- AC-6.1 Positive: Example E-4: Ben cancels; Cara is ineligible at that moment, Dev is eligible. Expected:
  bookings are Ana and Dev, Cara's entry is `skipped_ineligible`, the queue is empty. Surface: service
  reads; notifications. Confirm: contract test with a stubbed eligibility rule.
- AC-6.2 Failure: n/a: nobody eligible: the seat stays free and the class reopens for normal booking
  (covered by R-4 boundaries).
- AC-6.3 Boundary: every remaining entry is ineligible: all are skipped, the queue is empty, the seat is
  free, and no error reaches the member who cancelled. Surface: service. Confirm: contract test.
- Open: **G-1** and **G-2** (what "eligible" means and whether booking costs credits or money) block the
  detailed rule set; the skip behaviour itself is ready.

### R-7 A member can leave the waitlist

Behaviour: the member can remove their active entry at any time while it is active. Entries behind move up
one place. No seat is created or removed.
Boundaries: leaving is not cancelling a booking; it cannot trigger a promotion.
Error behaviour: leaving an entry that is not active returns `not_waitlisted` and changes nothing.
Consumer outcome: the class card returns to "Join waitlist" if still full.

- AC-7.1 Positive: Example E-2: continuing E-1, Dev leaves. Expected: Eli is #1; bookings unchanged (Ana,
  Cara); Dev's entry is `left`. Surface: member UI and service. Confirm: end-to-end test.
- AC-7.2 Failure: Dev leaves again: `not_waitlisted`, no change. Surface: service. Confirm: contract test.
- AC-7.3 Boundary: Eli, the only entry, leaves: the queue is empty. A later cancellation then frees a seat
  for normal booking. Surface: service. Confirm: contract test.

### R-8 Members are told about waitlist outcomes

Behaviour: the member is notified when promoted ("You have a spot in Spin, Tue 6:00 PM"), when skipped, and
when the class is cancelled while they were waiting (R-9). Notification uses the app's existing channel; if
none exists the in-app bookings area is the notice (G-3).
Boundaries: one notice per outcome; the in-app state is authoritative, the message is a courtesy.
Error behaviour: a failed delivery never reverses a promotion; the booking stays and the in-app state shows
it. A retry of delivery does not send a second notice for the same promotion.
Consumer outcome: a promoted member who never opens the app still learns of the seat if a channel exists,
and otherwise sees it on next visit.

- AC-8.1 Positive: in E-1, Cara receives exactly one promotion notice naming the class and time. Surface:
  the notification channel's outbox or the in-app list. Confirm: contract test with a fake channel.
- AC-8.2 Failure: the fake channel errors; Cara still holds the booking and sees it in the bookings area.
  Surface: service reads. Confirm: contract test with an injected failure.
- AC-8.3 Boundary: delivery retried after a timeout produces one notice. Surface: fake channel outbox.
  Confirm: contract test.
- Open: **G-3** (what channels exist).

### R-9 Waitlist ends with the class

Behaviour: when a class is cancelled, every active entry ends as `class_cancelled` and its member is
notified. When the class start time passes, every active entry ends as `class_started`. No promotion occurs
in either case.
Boundaries: what happens to existing bookings on class cancellation is existing behaviour (R-11) and is not
changed here. Rescheduling a class is not modelled (G-7).
Error behaviour: n/a: no member action is involved.
Consumer outcome: a member never sees an active "#n" for a class that is cancelled or over.

- AC-9.1 Positive: Example E-6: C1 with Dev #1 and Eli #2 is cancelled by staff. Expected: both entries
  `class_cancelled`, two notices, the class card shows the cancelled state. Surface: member UI; service.
  Confirm: contract test; UI test.
- AC-9.2 Failure: n/a: no failure path is specific to this clause beyond R-8 delivery failure.
- AC-9.3 Boundary: see AC-4.3: at exactly start time active entries read as `class_started`.

### R-10 Seat count and queue stay correct under simultaneous actions

Behaviour: whatever the interleaving of joins, leaves, cancellations and bookings, confirmed bookings never
exceed capacity, no member holds two seats or two active entries in a class, no entry is promoted twice, and
queue order follows PD-1 by a service-assigned order.
Boundaries: a join submitted twice (double click, retry) yields one entry and returns the same position.
Error behaviour: of two simultaneous requests competing for the last free seat, one succeeds and the other
gets a normal refusal; neither sees a partial state.
Consumer outcome: the displayed counts and positions are consistent with each other after any burst.

- AC-10.1 Positive (Example E-7): Fixture F; Ana and Ben booked; Cara, Dev, Eli waiting. Ana and Ben cancel
  simultaneously. Expected in either order: bookings are Cara and Dev, queue is Eli #1, no one is promoted
  twice. Surface: service reads after both complete. Confirm: concurrent contract test, repeated over both
  orders.
- AC-10.2 Failure: Ana and Ben booked, Cara waiting. Ben's cancellation and Fay's direct booking attempt run
  at the same time. Expected in either order: Fay is refused `class_full` (before the cancel the class is
  full; after it Cara holds the freed seat), bookings end as Ana and Cara, capacity is never exceeded, and
  the UI offers Fay the waitlist. Surface: service and UI. Confirm: concurrent contract test over both
  orders.
- AC-10.3 Boundary: Example E-3: Cara joins twice: both calls return position 1 and the queue holds one
  entry. Ana, holding a booking, is refused `already_booked` and no entry is created. Surface: service.
  Confirm: contract test.

### R-11 Existing booking behaviour is preserved

Behaviour: booking a class with a free seat and an empty waitlist, cancelling a booking, class listings, and
authorisation rules behave exactly as before this change, except that the full-class turn-away is replaced
by the offer of R-1 and a cancellation of a booking in a full class now triggers R-4.
Basis: S-1 asks only to change the full-class experience. Silence about the rest preserves it.
Evidence limit: no baseline was available, so "as before" cannot be checked until the existing behaviour is
recovered (G-1). The checks below are written against that recovered baseline.

- AC-11.1 Positive: a normal booking on a class with a free seat and no waitlist is unchanged. Surface: UI
  and service. Confirm: the existing booking tests re-run, plus one new regression case.
- AC-11.2 Failure: an unauthorised cancel stays refused and frees no seat. Surface: service. Confirm:
  existing tests.
- AC-11.3 Boundary: n/a: boundaries of existing behaviour are owned by the existing app's own requirements.

## Non-functional requirements

- **NFR-1 Integrity** (R-4, R-10). Observable: AC-10.1 to AC-10.3 pass under concurrent execution. Method:
  concurrent contract tests. Numeric concurrency or throughput bound: **unresolved** (G-8), as the request
  gives no volume and none is invented.
- **NFR-2 Authorisation and privacy** (R-3, PD-6). Server derives the member identity; the client cannot
  name another member. Another member's entry, position or identity is never returned. Logs carry opaque
  IDs only, no names or contact details. Method: AC-3.2 and a log inspection check.
- **NFR-3 Reliability and recovery** (R-4, R-8). Promotion is not lost on a process restart: a seat that was
  freed is either already promoted or the cancellation did not happen. Notification failure never changes
  booking state. Method: failure-injection contract tests (AC-8.2). Availability target: excluded; this
  request adds no new availability promise beyond the existing app's.
- **NFR-4 Latency and freshness**. A join, leave or cancel returns its outcome in the same interaction; the
  member's status is current on next load or refresh. Live push is not required. A numeric latency bound is
  **unresolved** (G-8), since the existing app's bound is unknown.
- **NFR-5 Compatibility**. The waitlist works on every client and runtime the app already supports; none
  is added. Method: run the end-to-end checks on the existing supported matrix (unknown until G-1).
- **NFR-6 Operability**. Events recorded, reusing the app's existing log or audit facility (unknown, G-1):
  joined, left, promoted, skipped, class-ended, each with class ID, entry ID and a timestamp. Method: assert
  the events for E-1 and E-2.
- **NFR-7 Designed interface** (applies because members use a UI). Observable criteria:
  1. Visual system. The waitlist surfaces inherit the app's existing identity, tokens and components
     (established product identity takes precedence; not verified here, G-1). Where a choice is
     unspecified, the starting point is the light expressive profile from the UI visual-direction guide: the
     light Gemini look with Material 3 Expressive principles, airy tonal rounded surfaces, a restrained
     accent, a clear humanist sans-serif from local fonts. Start appearance: light, with a dark option. All
     colours, spacing and type sizes come from named tokens with a light and a dark set.
  2. States. Designed empty (no waitlisted classes), loading (skeleton or inline progress), error with
     retry, pending ("Joining…", control disabled and announced) and success states. Success appears only
     after the service confirms; a timer or animation never stands for confirmation.
  3. Layout. Works at 320 px and at 1280 px with no horizontal overflow.
  4. Accessibility. Text contrast at least 4.5:1 and large text and control boundaries at least 3:1 in both
     themes (WCAG 2.x AA, SC 1.4.3 and 1.4.11); visible focus (SC 2.4.7); keyboard operation of
     join and leave; position changes announced through a polite live region; the status never conveyed by
     colour alone.
  5. Motion. Used only to explain a change (for example the card moving from "Join" to "On the waitlist,
     #n"); disabled under `prefers-reduced-motion`.
  6. One icon set, the app's existing one.
  Method: rendered checks at both widths and both themes, an automated contrast check, a keyboard-only run,
  a reduced-motion run. The concrete treatment is chosen at planning (AD-4).

### UI premises (components, interaction, skin)

- Components: the class card gains a state set: Book, Join waitlist, On the waitlist #n with Leave, Class
  closed. A "Waitlisted" group appears in My Bookings. A promoted booking carries a "from waitlist" label.
- Interaction: the member's draft intent (a pressed Join) is separate from confirmed server state. While a
  request is pending the control shows progress and is disabled. A late response from a superseded request
  does not overwrite a newer state. Leave asks for a short confirmation that states that rejoining goes to the
  back of the queue; no undo window exists.
- Skin: see NFR-7.1. Named visual reference: light Gemini, Material 3 Expressive (starting point only).

## State and data assessment

| Item | Owner and location | Who may read | Simultaneous changes | Ends and removal | Quotas and limits |
| --- | --- | --- | --- | --- | --- |
| Waitlist entry (class ID, member ID, status, service-assigned order, joined and resolved timestamps) | The booking service, in the same store and consistency scope as bookings (AD-1). Not on the client. | The entry's own member; no other member (PD-6). Staff: unresolved (G-6). | Serialised per class so order is unique and a seat is promoted once (R-10). | Final status on promote, leave, skip, class cancel or class start; record kept as long as booking records (PD-7, G-5). | Unknown platform limits (G-1). |
| Class seat count / bookings | Existing booking records, authoritative (R-11). | As today. | Same serialisation as above. | As today. | As today. |
| Client presentation state (pending join, error) | The member's UI only. | The member. | Latest request wins; superseded responses are discarded. | Discarded on reload; nothing persisted locally. | Browser quotas not touched. |
| Notification outbox / delivery record | The existing notification channel (G-3). | The recipient. | One notice per promotion (AC-8.3). | Per the channel's own policy. | Channel's own limits. |

Personal data: member ID in entries and logs. Shown only to the member. Stored with the booking data. Never
logged with names or contacts. Removed with the member's booking data by the app's existing account removal
process (G-5).

Before and after invariants: before and after every operation, bookings ≤ capacity; a member has at most one
of {booking, active entry} per class; entry order within a class is a strict sequence; if the waitlist is
non-empty and the class is open, no seat is free that an eligible entry could take.

Recovery: an operation fails as a whole (the cancellation and its promotion together); no repair job is
required. Unknown: whether the platform offers the transaction scope this needs (AD-1, G-1).

## Service boundaries

- Notification channel: authority is the booking service (the channel only carries a message). Freshness
  versus revocation: n/a, the message carries no data that grants access, and the UI always re-reads state.
  Incremental state: n/a, one message per outcome. Async completion and recovery: delivery is after the
  state change; failure never undoes it; retry is deduplicated by promotion ID (AC-8.2, AC-8.3). Event
  coverage: owned events in NFR-6; the channel's own delivery logs are reused where they exist.
- Payments or credits: **unresolved** (G-2). If a booking has a cost, promotion must apply the same
  charging rule with a defined outcome on failure.
- Identity provider, cache, queue, broker: not applicable; none is added. Promotion happens inside the
  cancelling operation, so no worker or scheduler owns work.

## Replayable examples (consolidated)

All use Fixture F. Status `NOT-REPLAYED: no product or runtime exists in this stage`. The expected results
were walked by hand from the rules above, with each action permitted by the named rule, and not by the
product under test.

| ID | Steps | Rule permitting each decisive step | Recomputed result |
| --- | --- | --- | --- |
| E-1 | Ana, Ben book; Cara, Dev, Eli join; Ben cancels. | Join: R-1, R-2 (full, open, not booked). Cancel: existing (R-11). Promote: R-4, R-5. | Join positions 1, 2, 3. Bookings Ana, Cara. Queue Dev #1, Eli #2. |
| E-2 | After E-1: Dev leaves; then Ana cancels. | Leave: R-7 (active entry). Cancel: existing. | After leave: queue Eli #1, bookings Ana, Cara. After cancel: bookings Cara, Eli; queue empty. |
| E-3 | Empty C1: Fay joins. Then Ana, Ben book; Ana joins; Cara joins twice. | R-2 (`class_not_full`, `already_booked`); R-10 (idempotent). | `class_not_full`; `already_booked`; positions 1 and 1; queue holds Cara once. |
| E-4 | Ana, Ben booked; Cara, Dev wait; Cara ineligible; Ben cancels. | R-4, R-6. | Bookings Ana, Dev; Cara `skipped_ineligible`; queue empty. |
| E-5 | Ana, Ben booked; Cara waits; Fay books; Ben cancels; Fay books again. | R-5 (`class_full`), R-4. | `class_full`; then bookings Ana, Cara; Fay again `class_full`. |
| E-6 | Ana, Ben booked; Dev, Eli wait; staff cancels C1. | R-9. | Dev, Eli `class_cancelled`; two notices. Existing bookings per existing behaviour. |
| E-7 | Ana, Ben booked; Cara, Dev, Eli wait; Ana and Ben cancel in either order. | R-4, R-10. | Order Ana then Ben: Cara, then Dev, promoted. Order Ben then Ana: same set. Bookings Cara, Dev; queue Eli #1. |
| E-8 | Ana, Ben booked; Eli waits; Ben cancels at exactly T0+48h. | R-4 and PD-3 (no promotion at or after start). | Bookings Ana only; Eli `class_started`. |

Examples E-4, E-6 and parts of E-8 depend on the app's eligibility, staff cancel and cancel-at-start rules,
which are unconfirmed (G-1): their start states are **open prerequisites**, not confirmed reachable.
A reference model of the rules for E-1 to E-8 was written in the run scratch area and not executed
(execution was not approved here), so the table above is a hand walk only.

## Open gaps

- **G-1** (blocks readiness of planning for R-4 triggers, R-6, R-11, NFR-5, NFR-6): there is no repository,
  discovery or baseline. Stack, existing booking and cancellation rules, eligibility conditions, staff
  actions (cancel a booking, edit capacity, cancel a class), notification code and the logging facility are
  unknown. Smallest confirming step: a discovery pass over the app's booking flow, the cancellation path and
  its tests. Safe interim: the behaviour specified here stands as the intended delta. Dependent: all
  implementation planning.
- **G-2** (R-4, R-6): does a booking cost money or credits at booking time? If yes, PD-2 (automatic
  promotion) must be revisited, probably to an offer with a claim window. A person must decide.
- **G-3** (R-8): which notification channels exist (email, push, SMS, in-app)? Interim: in-app only.
- **G-4** (R-1): should the waitlist length be capped? Interim: no cap.
- **G-5** (PD-7): retention period of finished entries and removal on account deletion. Interim: follow
  bookings. No period invented.
- **G-6**: do instructors or staff need to see or manage the roster? Interim: out of scope (PD-9).
- **G-7**: class rescheduling or edits to class start time while members are waiting. Interim: not modelled;
  the entry follows the class unchanged.
- **G-8**: numeric latency and concurrency bounds. Interim: none; observable pass/fail criteria only.
- No material requirement conflict is open.

## Domain rules left out (bounded under their R-<n>)

- R-1: no priority tiers (membership level, loyalty), no multi-class waitlisting in one action, no waitlist
  for recurring series as a whole.
- R-4: no claim window or "accept within N hours" step (PD-2); no overbooking to absorb no-shows.
- R-5: no manual reordering by staff, no paid priority.
- R-7: no "auto-rejoin" or snooze.
- R-8: no reminder or digest messages, no marketing use of waitlist data.
- R-9: no automatic suggestion of alternative classes.

## Requirement basis and change record

| R | Change | Basis (stable source) | Source locator | Evidence limit | Pending implementation and checks |
| --- | --- | --- | --- | --- | --- |
| R-1 | add | S-1 (request, 2026-11-21): "Add a waitlist to our class booking app" | S-1 whole sentence | no baseline | UI and service build; AC-1.1, AC-1.2 |
| R-2 | add | S-1; PD-3, PD-4, PD-5 | S-1 | no baseline | AC-2.2, AC-2.3 |
| R-3 | add | S-1 ("don't turn people away" needs the member to see their place); PD-6 | S-1 | none beyond defaults | AC-3.1 to AC-3.3 |
| R-4 | add | S-1 ("full classes don't turn people away"); PD-1, PD-2, PD-3 | S-1 | G-1, G-2 | AC-4.1 to AC-4.4 |
| R-5 | add | S-1; PD-1, PD-5 | S-1 | PD defaults unconfirmed | AC-5.1, AC-5.3 |
| R-6 | add | S-1 (promotion must work for real bookings); PD-2 | S-1 | G-1, G-2 | AC-6.1, AC-6.3 |
| R-7 | add | S-1 (a queue implies leaving it); PD-4 | S-1 | none | AC-7.1 to AC-7.3 |
| R-8 | add | S-1; PD-2 (automatic promotion needs the member told) | S-1 | G-3 | AC-8.1 to AC-8.3 |
| R-9 | add | S-1 (a waitlist for a class that no longer runs must end); PD-3 | S-1 | G-7 | AC-9.1 |
| R-10 | add | S-1 (a waitlist that overbooks defeats the booking app) | S-1 | platform consistency scope unknown | AC-10.1 to AC-10.3 |
| R-11 | preserve | S-1 changes only the full-class path | S-1 | no baseline, G-1 | AC-11.1, AC-11.2 |

The basis "S-1" is the request quoted above with its date; PD defaults are agent assumptions awaiting
confirmation and carry no user authority.

## Retired

None. This is the first specification for the product; nothing was dropped.

## Submission

- `summary`: Specification for adding a first-come, first-served waitlist to the class booking app: join a
  full class (R-1, R-2), see own position (R-3), automatic promotion on a freed seat (R-4) with a fairness rule
  against queue jumping (R-5), eligibility re-check (R-6), leave (R-7), notification (R-8), end with the
  class (R-9), concurrency-safe (R-10), and existing booking behaviour preserved (R-11). Assumptions taken
  unattended: PD-1 to PD-9 (notably PD-2 automatic promotion with no claim window, PD-3 waitlist closes at
  class start, PD-5 direct booking cannot jump the queue). **Open:** G-1 (no baseline or repository: planning
  for the existing-behaviour-dependent clauses stays unready), G-2 (cost at booking time could reverse
  PD-2; needs a person), G-3 to G-8. No material requirement conflict. Examples E-1 to E-8 are
  `NOT-REPLAYED` (no runtime); results walked by hand. `backchain-check` does not exist in this run and was
  not used. Nothing was executed or tested.
- `primary`: R-1, R-3, R-4, R-5.
- `evidence_refs`: KNOWLEDGE/spec.md (sections R-1 to R-11, Non-functional requirements, State and data
  assessment, Service boundaries, Replayable examples, Open gaps); KNOWLEDGE/architecture.md (AD-1 to AD-4);
  request S-1 (2026-11-21); guides read: behavioral-requirements.md (Behavior model, Traceability and review,
  Actors channels and state ownership), requirements-definition.md, platforms/ui.md (Light expressive starting
  point), service-discovery.md (Verification and Runtime state placement), current-system-baseline.md.
