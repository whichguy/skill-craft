# Class Booking App — Product Specification

Living product spec. This run adds the **class waitlist** (R-1..R-9). Structure and technology choices live in
`architecture.md` (AD-<n>), not here. Product decisions in this file are labelled **DD-<n>**.

## Baseline and sources

| Item | Status |
| --- | --- |
| Prior `KNOWLEDGE/spec.md` | None existed. This is the first spec; there are no earlier R-<n> to keep, change or retire. |
| Discovery / research results, repository, selected baseline | **None available** in this run. The existing booking app was not inspected. |
| Current-system baseline | **Unknown / not recovered** (gap G-1). Nothing below states what the app does today; every "preserved" clause is a requirement on existing behaviour, to be confirmed against the app. |
| Request (source of every R-<n>) | 2026-11-21: "Add a waitlist to our class booking app so full classes don't turn people away." |

Evidence kinds used below: **Request** (user words), **DD** (design default chosen here, not a user instruction,
revisable), **Unknown** (needs the baseline or a person).

## Product premises (assumptions, all revisable)

- A *member* books a seat in a scheduled *class* with a fixed *capacity*; a booking is *confirmed* and occupies one seat.
  (Unknown whether capacity, cancellation windows, credits or payment exist. See G-1, G-5.)
- Fixture used by every example: class **C-101 "Spin 18:00"**, capacity **2**, starts in the future, not cancelled.
  Members `ana`, `ben`, `cy`, `dee`, `eli`, all signed in as themselves, all able to book under the app's existing rules.
- **DD-1 Joining is an explicit opt-in action, separate from booking.** A plain book request on a full class is still
  rejected (no silent enrolment), because promotion later creates a real booking (possibly a charge or credit use) and
  the member must have chosen that.
- **DD-2 Promotion is automatic, in first-come order**, with no claim window or hold timer. The alternative (offer a hold
  and wait for the member to confirm within a window) is open gap G-2.
- **DD-3 A member sees only their own waitlist position**, never other members' identities or the total length
  (privacy; the request needs nothing more).
- **DD-4 The waitlist closes when direct booking closes** (the app's booking cutoff, else class start), so a promotion
  never creates a booking the member could not have made directly. Open as G-4.
- **DD-5 No waitlist history is kept** after an entry ends; the resulting booking (if any) is the record. Chosen to avoid
  retaining personal data the request does not need.

## Requirements

Acceptance line format: `R-n.k` — kind (positive / failure / boundary) — expectation — *surface* — *how confirmed*.
Surfaces: **UI** = member-facing booking UI; **API** = whichever service interface that UI calls (identified in G-1).
"Confirmed" means an automated check at the named surface using the fixture, run by a later stage; none has run.

### R-1 Join the waitlist when a class is full

Behaviour: when a class has no free seat, a member who is neither booked nor waitlisted can join its waitlist. A plain
book request on a full class is rejected with an outcome that offers the waitlist (not a dead end).
Boundary: "full" means confirmed bookings = capacity. Out of scope for this R: waitlist cap (G-3), guests/group joins,
paid or priority waitlists.
Error behaviour: every rejected join leaves bookings and waitlist unchanged.
Consumer outcome: on a full class the member sees "Join waitlist" where the app previously showed only "Full"/an error.

- **R-1.1 positive** — C-101 has `ana`,`ben` confirmed (2/2). `cy` joins → `cy` is waitlisted at position 1; confirmed
  count stays 2. *UI + API.* Confirmed by UI flow and API test.
- **R-1.2 failure** — `cy` submits a *book* request on full C-101 → rejected "class full" with the waitlist option
  offered; no booking, no waitlist entry created. *API + UI.* API test; UI shows the Join waitlist action.
- **R-1.3 failure** — `ana` (already confirmed) joins C-101's waitlist → rejected "already booked"; `cy` (already
  waitlisted) joins again → rejected "already waitlisted", position unchanged. *API.* API test.
- **R-1.4 boundary** — C-101 with only `ana` confirmed (1/2): `ben` joins → rejected "class not full – book instead";
  no entry created; booking `ben` then succeeds. This is the exact capacity edge (1 of 2 vs 2 of 2). *API.* API test.
- **R-1.5 failure** — a join with no signed-in session, or naming another member's id in the request, is rejected and
  creates nothing (identity comes from the session only). *API.* API test.

### R-2 Waitlist order and position visibility

Behaviour: waitlist order is first-come-first-served by the server's recorded join order; each waitlisted member can see
their own position and which classes they are waitlisted for.
Boundary: a member sees only their own position, never other members' identities (DD-3, privacy); staff views of
waitlists are not requested and out of scope (G-7). Positions are 1-based and contiguous.
Error behaviour: if position cannot be loaded the UI shows an error state, not a stale or guessed number.
Consumer outcome: the member's "my bookings" view shows C-101 as *Waitlisted — position N*, visibly distinct from *Confirmed*.

- **R-2.1 positive** — `cy` then `dee` join (full C-101) → `cy` position 1, `dee` position 2. *UI + API.* UI and API checks.
- **R-2.2 boundary** — `cy` leaves, or is promoted → `dee` moves to position 1 with no gaps (see R-3, R-4). *API.* API test.
- **R-2.3 failure** — the position endpoint/view for `dee` called with `cy`'s entry id returns not-found/forbidden and
  discloses nothing about `cy`. *API.* API test.
- **R-2.4 positive (ordering rule)** — two joins that arrive "simultaneously" are totally ordered by the server's single
  recorded sequence; both positions are distinct. Covered under R-8.1.

### R-3 Leave the waitlist

Behaviour: a waitlisted member can remove themself at any time before the entry ends (R-4, R-7).
Boundary: leaving is idempotent in effect; members behind move up one place; leaving never changes confirmed bookings.
Error behaviour: leaving when not waitlisted is rejected "not on waitlist" with no change.
Consumer outcome: the entry disappears from "my bookings", the class card offers "Join waitlist" again.

- **R-3.1 positive** — full C-101 (`ana`,`ben` confirmed), waitlist `[cy, dee, eli]` (`eli` position 3); `dee` leaves →
  waitlist `[cy, eli]`, `eli` position 2, `cy` still 1, confirmed unchanged. *UI + API.* UI and API checks.
- **R-3.2 failure** — `dee` leaves again → "not on waitlist", list unchanged. *API.* API test.
- **R-3.3 failure** — `ben` tries to remove `cy`'s entry → rejected, `cy` still waitlisted. *API.* API test.

### R-4 Automatic promotion when a seat frees

Behaviour: when a confirmed booking on a full class ends (member cancels, staff cancels it) or capacity increases, the
earliest eligible waitlisted member is given a confirmed booking for the freed seat, in the same atomic step as the
seat being freed. Direct bookers cannot take that seat ahead of the waitlist.
Boundary: one freed seat promotes one member; two freed seats promote two, in order. If nobody is eligible the seat stays
free and normal booking resumes. Confirmed count never exceeds capacity; promotion never reorders others.
Error behaviour: if the promotion cannot complete, the seat-freeing action and the waitlist are left unchanged
(all-or-nothing) and the failure is reported to the actor who triggered it.
Consumer outcome: the promoted member sees *Confirmed* for the class on next load without any action by them.

- **R-4.1 positive** — C-101 `[ana, ben]` confirmed, waitlist `[cy, dee]`; `ana` cancels → confirmed `[ben, cy]`, waitlist
  `[dee]` (position 1), confirmed count 2. *API + UI (cy's "my bookings").* API test, UI check.
- **R-4.2 boundary** — capacity-1 class, `ana` confirmed, nobody waitlisted; `ana` cancels → 0/1 and `dee` can book
  directly. *API.* API test.
- **R-4.3 boundary** — capacity raised 2→4 while waitlist is `[cy, dee, eli]` and 2 confirmed → `cy` and `dee`
  promoted (in that order), `eli` remains position 1, count 4/4. *API.* API test. (Applies only if the app lets staff
  change capacity; if it cannot, mark n/a after G-1.)
- **R-4.4 failure** — waitlist `[cy]`; a direct book by `eli` racing `ana`'s cancel never takes the seat: there is no
  observable moment with a free seat and a non-empty eligible waitlist, so `eli` gets "class full". *API.* Concurrency test (R-8.3).
- **R-4.5 failure** — an injected system fault while creating the promoted booking (not an ineligibility, which is R-5) →
  `ana`'s cancellation is also not applied, the waitlist is unchanged and `ana` gets an error she can retry. *API.* Fault-injection test.

### R-5 Promotion eligibility and skipping

Behaviour: promotion applies the same booking rules a direct booking would (G-1 lists them: e.g. account in good
standing, credits/payment, time conflicts). A head-of-list member who fails them is removed from the waitlist with
a reason, notified (R-6), and the next member is tried.
Boundary: skipped members are never charged; if all remaining members are ineligible the waitlist empties and the seat
stays free. Exact rules are Unknown until the baseline exists (G-1, G-5); this requirement fixes only the skip/remove/next behaviour.
Error behaviour: an ineligible member never blocks those behind them.
Consumer outcome: the next eligible member is confirmed; the skipped member sees the entry gone with a reason.

- **R-5.1 positive** — capacity 1, `ana` confirmed, waitlist `[cy, dee]`, `cy` fails the booking rules (fixture
  choice: `cy`'s account is blocked in the test data); `ana` cancels → `cy` removed (notified), `dee` confirmed, count 1/1. *API.* API test.
- **R-5.2 boundary** — same, but only `cy` waitlisted → `cy` removed, waitlist empty, class 0/1, `dee` can then book directly. *API.* API test.
- **R-5.3 failure** — a skipped member is not charged and has no booking record created. *API.* API test.

### R-6 Notify the promoted (or removed) member

Behaviour: a member whose waitlist entry ends by promotion or by system removal (R-5, R-7) is told, using the app's
existing member-notification path, and the outcome is also visible in their "my bookings" view.
Boundary: the notification is sent after the promotion commits and at-least-once; the member sees at most one
notification per entry outcome (dedupe by entry id). Channel is Unknown (G-6).
Error behaviour: notification failure never undoes a promotion; it is retried, and the booking view remains the source of truth.
Consumer outcome: `cy` receives "You're in: Spin 18:00" and finds *Confirmed* in the app.

- **R-6.1 positive** — R-4.1 → one promotion notice for `cy`, none for `dee`/`ben`. *Notification path + UI.* Check the outbound message log or test inbox.
- **R-6.2 failure** — notification provider rejects the send → `cy` is still *Confirmed*; a retry later delivers exactly one notice. *Notification path.* Fault-injection test.
- **R-6.3 boundary** — the commit succeeds and the process dies before sending → on restart the notice is still sent. *Notification path.* Restart test.

### R-7 Waitlist ends when the class closes

Behaviour: the waitlist stops accepting joins, and no promotion occurs, once the class can no longer be booked: at the
same cutoff that applies to direct bookings, or at the class start time if there is none (DD-4, G-4). If a class is
cancelled or removed, all its waitlist entries end and members are notified.
Boundary: entries are never silently left dangling past the class's end.
Error behaviour: a join after closure is rejected "class closed"; no entry created.
Consumer outcome: "Join waitlist" is not offered for a closed class; members still waitlisted at closure see the entry
end with a reason.

- **R-7.1 positive** — `ana`,`ben` confirmed; `cy` waitlisted; staff cancels C-101 → `cy`'s entry ends, `cy` notified,
  bookings handled by the app's existing class-cancellation behaviour. *API + notification.* API test.
- **R-7.2 boundary** — C-101 at its cutoff instant: a join one second before succeeds, one second after is rejected;
  a cancellation after cutoff does not promote. (Cutoff value is Unknown until G-1/G-4; the check uses the app's actual cutoff.) *API.* Test with a controllable clock.
- **R-7.3 failure** — joining a class already started → rejected, nothing created. *API.* API test.

### R-8 Integrity under concurrency and retries

Behaviour: waitlist and bookings stay consistent when requests overlap or repeat.
Invariants: confirmed ≤ capacity; each member has at most one entry or booking per class; waitlist order is a single
total order; each freed seat promotes at most one member exactly once even if the cancel event is retried.
Error behaviour: a retried identical request does not duplicate its effect; a losing concurrent request gets the
normal rejection (full / already booked), never a corrupted state.
Consumer outcome: no member is ever shown a booking the system later disowns.

- **R-8.1 boundary** — `cy` and `dee` send join at the same moment on full C-101: both succeed with positions {1,2} in
  some order, no duplicates, no gaps. *API.* Concurrent test.
- **R-8.2 failure** — `ana`'s cancel request delivered twice → exactly one promotion; confirmed count 2, not 3. *API.* Retry test.
- **R-8.3 boundary** — `ana` cancels while `eli` simultaneously books on C-101 with waitlist `[cy]`: result is `cy`
  confirmed and `eli` rejected "class full" (waitlist has priority); never 3 confirmed. *API.* Concurrent test.
- **R-8.4 boundary** — waitlist `[cy, dee]`; `cy` leaves at the same moment `ana` cancels. Exactly one of two outcomes:
  (a) cancel first: `cy` promoted, `cy`'s leave is then rejected (no longer waitlisted) and `cy` keeps the booking;
  (b) leave first: `dee` promoted. Never both promoted, never a seat left free while `dee` waits. *API.* Concurrent test.

### R-9 Waitlist entries are not bookings (preserve existing behaviour)

Behaviour (preserved): everything the app does today for non-full classes, cancellations, rosters, attendance, capacity
counts, billing/credits and reports is unchanged. A waitlist entry occupies no seat, is not on the roster, consumes no
credit and is charged nothing until promotion. Changed behaviour: only a *full-class* book request now carries the
waitlist offer (R-1.2).
Boundary: promotion is the only transition that turns an entry into a booking, and then the normal booking rules apply.
Error behaviour: n/a — no new error path beyond R-1..R-8.
Consumer outcome: staff roster for C-101 lists only confirmed members; occupancy shows 2/2 whatever the waitlist length.

- **R-9.1 positive** — C-101 2/2 with waitlist `[cy, dee]` → roster lists `ana`,`ben` only; occupancy 2/2. *Staff roster UI/API.* Check roster.
- **R-9.2 positive** — a non-full class: book, cancel, rebook flows behave as before this change. *UI + API.* Existing regression suite plus a new smoke case; **baseline unavailable** so the existing suite cannot be named (G-1).
- **R-9.3 failure** — waitlisted `cy` is not charged / loses no credit until R-4 happens. *Billing/credit surface.* Check balances before/after join.

## Worked scenario (replayable)

Fixture: C-101, capacity 2, future start, `ana`/`ben`/`cy`/`dee`/`eli` as above. Rules permitting each step in brackets.

| # | Actor action | Permitted by | Expected state after (confirmed / waitlist) |
| --- | --- | --- | --- |
| 1 | `ana` books; `ben` books | existing booking (free seats) | `[ana, ben]` / `[]` |
| 2 | `cy` book → rejected; `cy` joins; `dee` joins | R-1.2, R-1.1 | `[ana, ben]` / `[cy, dee]`; positions 1, 2 |
| 3 | `cy` joins again; `ana` joins | R-1.3 (both rejected) | unchanged |
| 4 | `ana` cancels | existing cancellation rule (**assumed**, G-1); R-4.1 | `[ben, cy]` / `[dee]`; `cy` notified once |
| 5 | `eli` joins | R-1.1 (class full again) | `[ben, cy]` / `[dee, eli]`; `eli` position 2 |
| 6 | `dee` leaves | R-3.1 | `[ben, cy]` / `[eli]`; `eli` position 1 |
| 7 | `dee` leaves again | R-3.2 (rejected) | unchanged |

Walk result: every action is permitted in the state the previous actions leave; the observer (each member's
"my bookings" view and the API reads in R-2) can see each expected result. Method: hand-walked against the rules above.
A model script `model.py` (in the run scratchpad) encodes these rules with permission checks before each action, but
**could not be executed in this run (command approval was not granted): NOT-REPLAYED, left open.** Nothing here claims
a product run; the existing app was not available.

## Retired

None.

## Non-functional requirements

Priority: correctness of seat accounting over speed. Nothing here invents a numeric bound; unresolved ones are listed.

- **NFR-1 Consistency under contention (accepted).** Operating condition: concurrent joins, leaves, cancels and books on
  one class. Required: R-8 invariants hold. Verification: concurrent/retry tests at API (R-8.1–R-8.4). Numeric load: **unresolved** (no traffic baseline, G-1); the tests use a small fixed fixture, not an SLA.
- **NFR-2 Responsiveness (unresolved bound).** Join, leave and position reads should feel immediate and give truthful
  feedback. Latency target: **unresolved**, needs the app's existing targets (G-1). Observable criterion now: no action leaves the UI
  in an unexplained pending state; each shows pending → confirmed or error.
- **NFR-3 Security / authorization (accepted).** Identity is taken from the session only; a member can read and change
  only their own entry (R-1.5, R-2.3, R-3.3). Verification: API tests above.
- **NFR-4 Privacy (accepted).** Waitlist entry data = member id, class id, join sequence, created-at. Shown: only to its
  owner (own position); never other members' identities. Stored: with the booking data store (AD-1). Logged: entry id and class
  id only, no names or emails. Kept: until the entry ends (promoted → becomes a booking; left/removed/expired → deleted).
  No separate history is retained (DD-5). Removed on account deletion, if the app has it (follows the app's existing deletion path; Unknown). Verification: log inspection test and API read tests.
- **NFR-5 Reliability / recovery (accepted).** Promotion is atomic with the seat release (R-4.5); notification is
  at-least-once after commit with dedupe (R-6.2, R-6.3). Verification: fault-injection and restart tests.
- **NFR-6 Observability (accepted, proportional).** Each promotion, skip and removal emits one structured log event with
  class id, entry id and outcome. Verification: log assertion in R-4.1/R-5.1 tests. No metrics platform required.
- **NFR-7 Compatibility (accepted).** Existing clients that book non-full classes are unaffected; a full-class book request is
  still rejected, with an added hint (R-1.2). Verification: existing regression suite (R-9.2, G-1).
- **NFR-8 Interface quality (accepted — applies because the member UI changes).** Observable criteria:
  1. Visual system: consistent spacing and type scales; a light theme and a dark theme from shared colour tokens.
  2. States: designed empty (no waitlisted classes), loading (join/leave pending), error (join failed, position
     unavailable) and success states for the waitlist UI, each reachable and checked.
  3. Layout: works at narrow (~360 px) and wide (~1280 px) with no horizontal overflow.
  4. Accessibility: visible keyboard focus; WCAG AA contrast (4.5:1 text, 3:1 large text/controls); waitlist status
     changes announced to assistive tech (e.g. "Waitlisted, position 2"), position not conveyed by colour alone.
  5. Motion only to explain a change (e.g. position moving up); honours reduced-motion.
  6. One icon set, the app's existing one.
  Visual reference: **the established product identity wins** (new waitlist elements inherit the app's tokens, appearance
  and components; not inspected here, G-1). Only where the app has no token for a choice, fall back to the
  light-expressive starting point: *light Google Gemini look and feel using Material 3 Expressive principles* (airy
  composition, tonal rounded surfaces, friendly type, one restrained accent, purposeful transitions), light first with dark option;
  the plan picks the concrete treatment and records it as an AD. Verification: browser check at both widths and both themes,
  automated contrast and keyboard-path check, reduced-motion check.
- **Excluded, with reasons:** throughput/capacity targets and availability SLA (no basis; app's own targets unknown, G-1);
  data migration (new entity only; nothing existing is rewritten, subject to G-1); regulatory retention (none identified in the request; Unknown).

## State and data assessment

| Resource | Owner / location | Change | Invariant before → after |
| --- | --- | --- | --- |
| WaitlistEntry (member, class, sequence, created-at) — **new** | Server-side booking store (AD-1) | created by join; deleted by leave/promote/remove/close | one entry per (member, class); sequence unique per class; positions contiguous 1..n |
| Booking (existing) | existing booking store | created by promotion (R-4), cancelled by existing flow | confirmed ≤ capacity; a (member, class) has booking xor entry |
| Class (existing: capacity, start/cutoff, cancelled) | existing | **read** (and observed when capacity changes) | not changed by this feature |
| Notification record/outbox | existing notification path | created after commit | at most one visible notice per entry outcome |
| Member credit/payment balance | existing | untouched until promotion; then via normal booking rule | no charge for waitlisted/skipped members (R-5.3, R-9.3) |

Recovery: promotion and seat release commit together or not at all; unsent notices resend after restart; no entry survives
its class. Applicable checks: R-4.5, R-6.2–R-6.3, R-8. Unknowns: actual store type and transaction scope (G-1); whether staff can change capacity (R-4.3).
Client state: the UI holds only presentation and pending-intent state; position and booking status are re-read from the server.
Quotas/limits: none known; per-class waitlist cap deliberately unset (G-3), so no quota is claimed.

## Service boundaries

- **Booking store (the app's own backend):** current authority for seats and entries; every join/leave/promote reads and
  writes it directly, no cache of seat availability may decide a join or promotion (freshness: authoritative read at action time;
  displayed counts and positions may be stale and are re-read on action; a stale UI action is rejected by the R-1/R-3 rules, not trusted).
- **Notification path (existing, Unknown):** the only plausible external boundary. Acknowledgment from the provider means
  accepted, not delivered; completion is asynchronous and recovered by retry (R-6). Owned event coverage: promotion, skip
  and class-closure removal events logged (NFR-6).
- Not applicable: incremental remote sync, revocation caches, subscriptions/push of live position (members see updated positions on next load; live push is not requested).

## Information lifecycle summary

| State | Owner/location | Who reads | Simultaneous changes | Ends / removed |
| --- | --- | --- | --- | --- |
| WaitlistEntry | server booking store | its member (own position), the system | single total order per class (R-8) | promoted, left, removed (R-5), class closed/cancelled (R-7) |
| UI pending/draft state | client memory | the member | n/a — re-read from server on result | on completion or reload |
| Notification | existing path | the member | dedupe by entry id | per existing notification retention (Unknown) |

No identity, sharing or persistence beyond this is added.

## Request-outcome traceability

| Request outcome | Acceptance lines |
| --- | --- |
| "Add a waitlist" — members can queue for a full class | R-1.1–R-1.5, R-2.1–R-2.4, R-3.1–R-3.3 |
| "so full classes don't turn people away" — a full-class member is not a dead end and actually gets a seat when one opens | R-1.2, R-4.1–R-4.5, R-5.1–R-5.3, R-6.1–R-6.3, R-7.1–R-7.3 |
| Implicit: existing booking behaviour intact | R-9.1–R-9.3, NFR-7 |
| Implicit: seats never oversold | R-8.1–R-8.4, NFR-1 |

Domain rules the request leaves out, listed under the R they bound: waitlist cap and paid/priority waitlists (R-1,
G-3); guests/group joins (R-1); staff view/manage waitlist (R-2, G-7); claim windows (R-4, G-2); membership-tier priority (R-4);
cancellation penalties for promoted members (R-4, G-5); recurring-series waitlists (R-1).

## Open gaps (unresolved prerequisites and decisions)

- **G-1 (blocks planning of implementation tasks; behaviour clauses stand)** — no discovery/baseline of the existing app: stack,
  data store and transaction scope, API/UI surfaces, booking/cancellation/cutoff rules, credits/payments, roles,
  notification channel, existing regression suite. Smallest confirming observation: read the repo README and booking module,
  run its existing tests. Owner: discovery. Under R-1, R-4, R-5, R-6, R-7, R-9.
- **G-2** — automatic promotion (DD-2, assumed) vs offer-with-claim-window. Product owner decision. Under R-4.
- **G-3** — waitlist length cap. Assumed none. Under R-1.
- **G-4** — promotion/join cutoff: assumed same as direct-booking cutoff, else class start (DD-4). Under R-7.
- **G-5** — how credits, payment, cancellation penalties apply to a promoted booking. Assumed: same rules as a direct booking at promotion time. Under R-5, R-9.
- **G-6** — notification channel(s). Assumed: the app's existing booking-confirmation channel plus in-app status. Under R-6.
- **G-7** — staff visibility of waitlists. Not requested; excluded. Under R-2, R-9.

## Pending implementation and checks

All of R-1..R-9 and NFR-1..8 are **proposed, unimplemented and unverified**. No test has been written or run. The worked scenario is
hand-walked only (see above).

## Submission

- **summary:** First spec for the class-booking-app waitlist: nine requirements (R-1 join when full, R-2 order/position, R-3 leave,
  R-4 automatic promotion on freed seat, R-5 eligibility skip, R-6 notification, R-7 closure, R-8 concurrency integrity,
  R-9 preserve existing behaviour), eight NFRs, state/data and service-boundary assessment. **Open:** the existing app was not
  inspected, so G-1 (baseline) keeps implementation planning unready; G-2..G-7 are product choices with the assumed defaults above
  (auto-promotion, no cap, same cutoff as direct booking, same booking rules at promotion, existing notification channel, no staff view).
  Assumptions: explicit opt-in join (DD-1); only own position visible (DD-3); no waitlist history kept (DD-5). The worked scenario
  could not be executed (command approval not granted): NOT-REPLAYED. No requirement conflict found.
- **primary:** R-1, R-4
- **evidence_refs:** KNOWLEDGE/spec.md (sections R-1..R-9, Non-functional requirements, State and data assessment, Service boundaries,
  Information lifecycle summary, Open gaps); KNOWLEDGE/architecture.md (AD-1..AD-3); GUIDES/behavioral-requirements.md#behavior-model,
  #traceability-and-review, #actors-channels-and-state-ownership; GUIDES/requirements-definition.md; GUIDES/service-discovery.md#verification;
  GUIDES/platforms/ui.md#light-expressive-starting-point; the request text of 2026-11-21. No repository, discovery, research or
  backchain receipt exists (duty 11 omitted).
