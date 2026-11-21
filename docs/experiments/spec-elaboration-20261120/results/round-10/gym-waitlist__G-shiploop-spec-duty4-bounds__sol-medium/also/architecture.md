# Class Booking App Architecture

## Decisions

### AD-1 — Booking and waitlist consistency boundary

**Status** — Unresolved. R-1 through R-3 require authoritative capacity, enrollment, authorization, and read-back across the existing booking and new waitlist actions. Preserve the booking authority and evaluate extending its existing consistency boundary first. If the current runtime cannot coordinate all relevant writers there, evaluate an existing conditional update or reconciliation capability against the same invariants before selecting a structure. The app, runtime, stores, deployed principal, operations, and permission observations are unavailable in this stage. No technology is selected.

**Handoff.** Use the specification's service-boundary and state clauses to locate the actual authority and mutation paths. Confirm that the real runtime can coordinate enrollment, seat assignments, withdrawals, and all relevant booking writers, and verify read-after-write and revocation on the actual member boundary. Establish applicable runtime quotas, existing observability and access, and retention and recovery support. A member view is a status consumer. If the selected flow needs independent execution, assign recovery to an authorized runtime owner and verify it with the view closed. Keep implementation decisions here and product policy under the affected requirements in `spec.md`.

**Revalidation.** Reopen on identification of the platform, booking writer inventory, actual target and principal permissions, or allocation policy. A change to any of those inputs can affect the eligible structure and its checks.
