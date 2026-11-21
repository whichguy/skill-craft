# Class Booking App: architecture

Evidence limit: no repository was available to the spec stage, so the stack and structure are **unknown**. The
decisions below are proposals to be validated against the real stack at discovery; they carry no technology
names on purpose.

## Stack

none recorded: unknown until discovery reads the repository (spec gap G-0).

## Structure

none recorded: unknown (G-0). Waitlist logic belongs in the same service module that owns bookings (AD-1).

## Conventions

none recorded.

## Interfaces and boundaries

The booking service is the single authority for bookings and waitlist entries. Clients are presentation only.
Notification delivery is the only outward hop and is asynchronous after commit (AD-3).

## Real-boundary checks

Concurrency (spec NFR-conc), failure injection during promotion (R-4:A6) and notification failure (R-6:A2) can
only be proven against the real store and service, not a mock. Owner: test strategy stage.

## Decisions

- **AD-1 (proposed): waitlist entries live in the same authoritative store as bookings, and promotion runs in
  the same unit of work as the event that opens the place.** Why: invariants I1-I4 (R-5) and the atomicity
  requirement (R-4:A6) need the cancel, the promotion and the order assignment to commit or fail together
  and to be serialised per class. Alternatives: a separate waitlist store with a reconciling job (rejected: a
  window where a free place and a waiting member coexist); a client-side queue (rejected: no authority).
  Status: proposed; validate that the real store can serialise per class.
- **AD-2 (proposed): end of an entry at class start is evaluated lazily against the class start instant, not by a
  scheduled job.** Why: correctness then needs no clock job; a sweep may be added later only for tidiness.
  Alternatives: a scheduler (rejected: new moving part for a rule that can be derived). Status: proposed.
- **AD-3 (proposed): notifications are sent after the promotion commits, reusing the app's existing channel; the
  booking is the truth and delivery failure is recorded, never rolled back.** Why: R-6. Alternative: send
  inside the transaction (rejected: a slow or failing channel would block or undo bookings). Status: proposed;
  depends on the unknown channel (G-6).

## Superseded

none
