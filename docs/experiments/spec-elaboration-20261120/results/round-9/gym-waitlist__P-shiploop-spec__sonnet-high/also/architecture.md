# Class Booking App: Architecture

How the product is built. What it must do is in `KNOWLEDGE/spec.md`; this file restates none of it.
Decisions are `AD-<n>`. Every entry below is **proposed**: no repository or baseline was available, so none is
checked against the real stack (spec G-1). Revalidate each after discovery of the app.

## Decisions

### AD-1 Waitlist state lives with the booking records, in one consistency scope (proposed)

- Decision: store waitlist entries in the same store as bookings and change both under one atomic,
  per-class serialised operation, with the order key assigned by the service.
- Serves: R-4, R-5, R-10, NFR-1, NFR-3.
- Alternatives: a separate store or service for the waitlist (rejected: promotion and cancellation could
  diverge and need compensation); client-held state (rejected: not authoritative, readable only by one client).
- Evidence limit: whether the existing store offers a transaction or conditional-write scope per class is
  **unknown**. If it does not, this decision is unresolved and the plan must add a per-class lock or
  conditional version check first.
- Revalidate when: the storage technology is discovered or changes.

### AD-2 Promotion runs inside the seat-releasing operation, with no queue or scheduler (proposed)

- Decision: cancelling a booking (and each other seat-freeing action the app already has) calls the
  promotion step synchronously within AD-1's atomic operation.
- Serves: R-4, R-6, R-10, NFR-3. Chosen because PD-2 has no timers; a broker or worker would add a
  dispatch and recovery owner that nothing requires.
- Revalidate when: G-2 reverses PD-2 (a claim window needs an expiry owner), or booking gains a payment step.

### AD-3 Notifications are sent after commit through the existing channel, deduplicated by promotion ID (proposed)

- Decision: emit the message once the state change is durable; a send failure is logged and retried without
  touching booking state; a duplicate-suppression key is the promotion's entry ID. The in-app state is
  the authoritative notice.
- Serves: R-8, NFR-3. Evidence limit: the existing channel is unknown (G-3).
- Revalidate when: a channel is identified.

### AD-4 UI treatment follows the existing identity, with the light expressive profile as fallback (proposed)

- Decision: reuse the app's existing components, tokens and icon set; where a visual choice is unspecified use
  the light expressive starting point (light Gemini look, Material 3 Expressive principles) with a dark
  option, as tokens. The plan selects concrete token values and the typeface from fonts available locally.
- Serves: NFR-7. Evidence limit: the existing identity was not inspected. No design skill or toolkit
  version was identified in this stage, so none is claimed.
- Revalidate when: the existing UI is inspected.
