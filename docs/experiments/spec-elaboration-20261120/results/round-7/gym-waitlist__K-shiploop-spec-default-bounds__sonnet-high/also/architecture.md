# Class Booking App: architecture

Status: written by the spec stage with **no repository, discovery or research result available**. Nothing here was
observed in code. Every decision is `Proposed` and stack-neutral; the plan stage confirms or supersedes each one
against the real stack (open gap G-1 in `spec.md`).

## Stack

Not inspected. Language, framework, datastore, notification provider and UI toolkit are unknown (`spec.md` G-1).
No technology is chosen by this stage.

## Structure

Not inspected. The waitlist is specified as an extension of the existing booking module's authority over class
capacity; it adds no new service (`spec.md` "Service boundary contracts").

## Conventions

- Names and shapes only; no secrets recorded.
- Requirement IDs `R-<n>` live in `spec.md`; decisions here are `AD-<n>`.

## Interfaces and boundaries

- Booking authority (existing, unseen): owns class capacity, bookings and, after this change, waitlist entries.
- Notification channel (existing, unseen): receives post-commit messages; never an authority for booking state.

## Real-boundary checks

| Check | Owner | Why a local test cannot prove it |
| --- | --- | --- |
| Promotion is atomic under concurrent cancellations and joins (`spec.md` R-8.1 to R-8.5) | test-strategy / test stage | Needs the real datastore's isolation behaviour, not a mock |
| Promotion notification reaches the real channel in a sandbox (R-6.1) | test stage | Needs the real provider or its sandbox |
| Position and booking state are server-authoritative in the browser (R-3, R-9.3) | product-acceptance | Needs a real browser session and sign-out/sign-in |

## Decisions

### AD-1: Promotion is one all-or-nothing operation owned by the booking authority
- Status: Proposed
- Choice: freeing a spot, choosing the first eligible waitlist entry, removing that entry and creating the booking
  commit together or not at all, inside the existing booking authority.
- Why: R-5 and R-8 forbid any observable state where a spot is free while an open waitlist is non-empty, a double
  promotion, and overbooking.
- Alternatives: a background worker that promotes later (rejected: opens a window where a direct booking can jump
  the queue, and adds an async owner); client-driven promotion (rejected: untrusted).
- Unverified prerequisite: the existing datastore can make these steps atomic (`spec.md` G-6). If it cannot, this
  decision is superseded and R-8 stays the requirement.

### AD-2: Waitlist closing is derived from the server clock at the time of each request
- Status: Proposed
- Choice: "open" or "closed" is computed from the class start instant and the server clock whenever a join, leave,
  promotion or view is evaluated. No scheduled sweep changes entries at the cutoff.
- Why: spec decision PD-3 and PD-5 need the cutoff to be exact (R-1.3, R-7.3) and need no cutoff notification, so a
  job would add an owner and a failure mode without adding behaviour.
- Alternatives: scheduled expiry sweep (rejected for now: only needed if a cutoff notice is later required).

### AD-3: Order is a server-assigned sequence, not client time
- Status: Proposed
- Choice: each entry gets a per-class, strictly increasing sequence value when it is appended; position is the count
  of entries with a lower sequence, plus one.
- Why: R-2 requires no ties and no dependence on client clocks; concurrent joins (R-8.2) still get distinct,
  contiguous positions.
- Alternatives: join timestamp (rejected: ties and clock skew).

### AD-4: Notifications are sent after commit and never roll back a booking
- Status: Proposed
- Choice: the promotion commit does not wait for, and is not undone by, notification delivery. A failure is logged.
- Why: R-6.2. A booked member must stay booked even if the channel is down. Retry policy is open (`spec.md` G-7).
- Alternatives: transactional outbox (deferred: only worth it if G-7 resolves to guaranteed delivery).

## Superseded

None.
