# Class Booking App — Architecture

Structure and technology decisions only. Product behaviour is in `KNOWLEDGE/spec.md` (`R-<n>`). The existing app's stack
was not inspected (spec G-1), so these decisions are stack-neutral and name no framework, database or library. Each
states what the plan must confirm.

## Decisions

### AD-1 Promotion runs inside the spot-opening change, serialised per session
- **Decision:** the cancel / staff removal / capacity change and the promotion procedure form one atomic unit of work,
  and all changes to one session (book, cancel, join, leave, capacity, close) are applied one at a time per session.
- **Serves:** R-5, R-9, A-11.
- **Why:** the invariant "no free spot beside a WAITING entry" holds at rest only if no other change can slip between the
  spot opening and the promotion. Cross-session parallelism stays.
- **Alternatives rejected:** a background promoter after the cancel commits (leaves a window where a direct booker takes
  the spot ahead of the queue, and needs reconciliation); a client-driven claim (needs a hold state, conflicts with A-2).
- **To confirm at plan:** the existing datastore offers a per-session lock, serialisable transaction or equivalent (G-6).
  If it does not, this decision is revisited before R-9 is planned; the required behaviour in R-9 does not change.

### AD-2 Waitlist entry is its own record; promotion creates an ordinary booking
- **Decision:** a new waitlist-entry record (member, session, state, join time, state-change time, reason). Promotion
  writes a normal confirmed booking through the same booking creation path as a direct booking (including its rules).
- **Serves:** R-5, R-7, R-11, A-5.
- **Why:** existing booking reads, cancellation and reports keep working unchanged; the booking rules stay in one place.
- **Alternatives rejected:** a "waitlisted" status on the booking record (every existing booking read would have to
  exclude it, putting R-11 at risk).

### AD-3 Position and waiting count are derived, never stored
- **Decision:** position = 1 + WAITING entries with earlier join order; computed on read.
- **Serves:** R-3.
- **Why:** leave/promote/skip/close would otherwise require renumbering many rows and could leave gaps or duplicates.
  With at most 10 WAITING entries per session (A-1) the read is bounded.

### AD-4 Notices are recorded with the transition and delivered afterwards (outbox)
- **Decision:** the notice record is written in the same unit of work as the entry transition; a separate delivery step
  sends it and marks it delivered; retries reuse the same record.
- **Serves:** R-6, NFR-3, A-6.
- **Why:** a delivery failure can neither undo a promotion nor produce a second notice.
- **To confirm at plan:** the existing notification mechanism and its failure behaviour (G-4); the retry bound is unresolved (G-8).

### AD-5 Closure at the start instant is enforced by guards and reported by derivation
- **Decision:** every join, leave and promotion checks "session bookable now" (not cancelled, `now < start`); a read at
  or after the start reports WAITING entries as CLOSED(class_started), and a periodic step stores that state later.
- **Serves:** R-8, A-3.
- **Why:** correctness does not depend on when a background step runs. The clock is injectable for tests (NFR-8).

### AD-6 Retention is a periodic deletion of terminal entries
- **Decision:** a periodic step deletes terminal entries 90 days after session start (A-7); WAITING entries are never
  deleted by it.
- **Serves:** R-10.

### AD-7 Interface treatment is recorded by the plan
- **Decision:** left to the plan: the concrete palette, type scale, spacing scale and shapes for the new waitlist UI,
  inheriting the existing app's tokens (G-1) and otherwise the light expressive starting point named in NFR-9.
- **Serves:** NFR-9.
- **Why:** the existing visual system must be read first; choosing it here would be guessing.
