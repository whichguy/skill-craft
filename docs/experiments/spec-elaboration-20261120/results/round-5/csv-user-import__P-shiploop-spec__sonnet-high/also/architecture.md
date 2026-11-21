# Architecture: User Administration

How the product is built. What it must do lives in `spec.md`; this file never restates requirements. Decisions are
AD-<n>. The host stack is **unknown** (spec G-1, G-7), so each decision is stack-neutral and says what must be
confirmed before it is relied on. No claim below about a library or platform capability is made; each must cite primary
documentation or a probe result when a concrete technology is chosen.

## Decisions

### AD-1 Synchronous request/response import
- **Decision:** the import runs inside one HTTP request: authorize, parse, validate, commit, audit, respond. No queue,
  worker, polling or job record.
- **Why:** the request needs one outcome the admin waits for (spec R-5: `201` means committed); an asynchronous design
  would add accepted-but-unprocessed work, restart recovery and a status surface the request did not ask for.
- **Serves:** R-4, R-5, R-6, R-8. **Alternatives considered:** background job with status polling (rejected unless M is
  too large for the host's request time limit).
- **Revisit when:** G-3 resolves to an M that cannot be processed within the host's request time limit (R-11).
- **Unverified:** the host's request time and body size limits.

### AD-2 Atomic commit and uniqueness owned by the user store
- **Decision:** all rows are inserted in one transaction, or one equivalent atomic operation, of the host's user store;
  a uniqueness constraint on the canonical (lower-cased) email in the store is the final arbiter, in addition to the
  pre-check that produces row-level `email_exists` findings. A constraint violation at commit rolls back the whole
  unit and is reported as `email_exists` (T-7). CSV parsing uses the runtime's maintained CSV library, not a hand-written
  splitter, configured for the rules in R-2 (quoted newlines, BOM, line ends).
- **Serves:** R-4, R-6, R-2. **Alternatives considered:** pre-check only (rejected: races, R-6); per-row inserts with compensation (rejected: partial effects, PD-1).
- **Unverified:** that the host's store supports a case-insensitive or canonical-form unique constraint and a multi-row
  transaction; that the chosen CSV library handles each R-2 case. Both need a probe or primary documentation at plan time.

### AD-3 Interface: one multipart endpoint plus one admin page
- **Decision:** `POST /api/admin/user-imports`, `multipart/form-data`, a single file part named `file`; responses as in
  spec R-5. The admin page calls it with `fetch`/XHR, using the host's session credentials and anti-forgery mechanism
  (R-10). The page is a component within the host's admin console and inherits its UI stack and identity; if none exists,
  R-13's starting point applies and a concrete UI AD is added at plan time.
- **Serves:** R-1, R-5, R-8, R-10, R-13. **Alternatives considered:** a CLI or script (not requested).
- **Unverified:** the host's route conventions, API prefix, and upload size limit. A host convention wins; the path and
  part name change here and in the test fixtures, with no change to the R-<n> text.

## Configuration surface (no values invented)
- Maximum rows **M** and maximum bytes **B** (spec G-3): configured values read at request time, so tests can set small
  ones (spec AC-2.5). Their production values are unresolved.

## Test-environment prerequisites (owners: test author)
- A fault-injection point on the user-store write (spec AC-4.3).
- A network stub with controllable response completion (spec AC-8.4, AC-8.5).
- A way to capture log output, the audit sink, outbound mail and the request-scoped temp location (spec AC-7.x, AC-9.2).
