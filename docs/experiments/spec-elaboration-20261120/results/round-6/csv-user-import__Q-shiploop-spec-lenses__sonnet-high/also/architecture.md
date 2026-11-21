# Architecture: Admin User Management

Written by the spec stage on 2026-11-21. The runtime, language and store are **unidentified** (no repository),
so these decisions are stated at the level the spec's requirements force and are provisional until discovery
names the platform (spec G-3). Product behaviour lives in `spec.md`; only structure and technology choices live here.

## Decisions

### AD-1 Atomic commit and store-enforced uniqueness
Serves R-6, R-11. The N users and the audit record are written in one store transaction; the unique-email guarantee
is a store constraint on the normalized email, not only a pre-check. The pre-check exists to produce the full
error report; the constraint decides races. Consequence: the store must offer a transaction spanning N inserts plus
the audit insert and a unique index (unverified here, spec G-3). If it does not, spec A-4 is not achievable and the
owner must choose again before R-6 is ready.

### AD-2 Synchronous request, bounded in memory
Serves R-2, R-16; assumption A-9. One multipart request carries the file and receives the final result. The body is read
with a hard byte cap (stop at cap + 1), decoded as strict UTF-8 and parsed in memory with the row cap applied while
reading. No background job, queue or stored upload. Revisit if the platform request timeout cannot fit 1,000 rows
(spec G-3).

### AD-3 Test seams
Serves R-11, R-12 and AL-6.3, AL-8.3, AL-9.4, AL-11.3, AL-12.4. The commit step is reachable through a narrow
interface so tests can inject a store failure, a mail failure, an audit-write failure, and can pause before commit.
The seam is compiled out or inert in production configuration.

### AD-4 Visual direction recorded for the import page
Serves R-17. If the product has an identity, inherit it (spec G-9). Otherwise: light theme first, dark theme by system
preference with a manual override; Material 3 Expressive proportions with the Gemini-style light palette (soft tinted
surfaces, one saturated accent), local sans-serif font stack with fallbacks, design tokens for spacing, type and colour in
one place, one icon set. The upload area and result summary are the focal point. Concrete token values are chosen by the
plan and checked against R-17's observable criteria.
