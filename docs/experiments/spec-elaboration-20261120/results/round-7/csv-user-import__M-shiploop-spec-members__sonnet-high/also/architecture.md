# Architecture decisions — User Administration

Structure and technology choices only; product decisions (for example all-or-nothing versus partial import, G-4) live in
`spec.md`. All decisions are proposed on 2026-11-21 without sight of the existing repository and must be reconciled against it
at plan time. They name no framework, language or product.

## Decisions

### AD-1 Validate everything, then commit once in a single atomic unit
Source: R-6, T-5…T-9. Parse and validate the entire file in memory first and collect every error; only if there are none, open
one transaction (or the store's equivalent atomic unit), insert all users and commit. Alternative considered: insert row by row
and compensate on failure — rejected because compensation can itself fail and leaves a visible partial state. Consequence: the
bound in R-9 also bounds memory and transaction size. Check: TC-6.2, TC-6.5.

### AD-2 Synchronous request/response, no job queue
Source: R-9, section 7. The HTTP response is the completion signal. Alternative considered: asynchronous job with a status
endpoint — deferred because no file size has been requested that needs it (G-2); revisit only if the chosen limits exceed what
one request can complete within the platform's timeout. Check: timing at the limit once G-2 is decided.

### AD-3 Store-level uniqueness as the arbiter of email conflicts
Source: R-5, T-7. Uniqueness on the normalised (lowercased, trimmed) email is enforced by a unique constraint or equivalent in
the user store, in addition to the application's pre-check, so concurrent imports and other creators cannot both win. If the
existing store lacks a case-insensitive uniqueness guarantee, adding it is a migration to be planned with a survey of existing
case-variant duplicates first (unknown, G-5). Check: TC-5.3.

### AD-4 Strict UTF-8 decoding and a maintained RFC 4180 parser
Source: R-2, R-3. Decode the upload strictly as UTF-8 (BOM tolerated), and parse with the platform's maintained CSV
parser rather than splitting on commas, so quoted commas, doubled quotes and embedded line breaks behave as R-2 states. The
chosen library is a plan decision; it must reject unterminated quotes (`MALFORMED_CSV`) instead of guessing. Check: TC-2.2,
TC-4.1.
