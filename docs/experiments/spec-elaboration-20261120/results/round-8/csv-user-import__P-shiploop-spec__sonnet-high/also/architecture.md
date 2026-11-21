# Architecture decisions

Structure and technology choices for the product described in `spec.md`. Product decisions never live here. No
repository existed when these were written, so every decision is **proposed or unresolved** and must be revalidated
against the real stack by the plan's first work item (spec gap G-7). No platform or library capability is asserted:
each claim below that depends on one is a question to confirm from primary documentation or a probe.

## Decisions

### AD-1 Atomic creation of all rows, with the audit record, in one unit of work
- **Status:** proposed; unresolved until the user store is known.
- **Serves:** R-5, R-7, R-9; transitions T-5, T-9, T-10.
- **Decision:** create all users and the audit record inside a single atomic unit of the user store, so a failure
  anywhere leaves nothing. If the store cannot commit this many records atomically, the alternative is a staged
  create with compensation, which weakens R-5 and needs a spec revision first. It does not silently replace it.
- **To confirm:** the store's transaction scope and the maximum unit size against the row limit (G-4).
- **Revalidate when:** the store is identified or the row limit is set.

### AD-2 Completion within the request versus a background job
- **Status:** unresolved.
- **Serves:** R-6, R-7, R-12; spec "Service boundaries".
- **Decision:** the default is to process synchronously inside the request and return the terminal outcome, when the
  row limit keeps processing within the host's request limit. Choose a durable background job only if G-4 and G-5 show
  that it does not fit. A job requires a durable operation record, an owner for abandoned work, an authorized status
  lookup, and a spec revision of R-6, R-7 and R-10 for the asynchronous contract.
- **To confirm:** host request limits and measured processing time at the row limit (G-5).

### AD-3 Stream-bounded, non-retaining file handling
- **Status:** proposed.
- **Serves:** R-2, R-8, R-11.
- **Decision:** enforce the byte limit while reading the body, so an oversized upload is cut off early. Hold file bytes
  only in request memory or request-scoped temporary storage, deleted on every outcome. No durable copy.
- **To confirm:** that the host framework exposes the body incrementally and cleans temp files on abort.

### AD-4 One import operation behind every consumer
- **Status:** proposed.
- **Serves:** R-1 to R-10; A-1 and G-1.
- **Decision:** the screen and any other client call a single import operation that owns authorization, parsing,
  validation, commit and reporting. The screen contains no business rules beyond convenience checks. This keeps the
  surface choice (G-1) from changing behavior.

### AD-5 Uniqueness enforced by the store, not only by a prior check
- **Status:** proposed; unresolved until the store is known.
- **Serves:** R-5, R-7; T-9.
- **Decision:** the validation-time EMAIL_EXISTS check is advisory for good reports. The authoritative guard is a
  uniqueness constraint on the normalized email inside the AD-1 unit, so concurrent imports cannot both create it.
- **To confirm:** the store supports a uniqueness constraint (or equivalent conditional write) on the normalized
  email, and the existing single-user creation uses the same rule.

### AD-6 UI direction (recorded for the plan to concretize)
- **Status:** proposed; defers to any established product identity (G-1).
- **Serves:** R-10, R-14.
- **Decision:** light-first theme with a dark option, following the light Gemini look with Material 3 Expressive
  principles (UI visual-direction guide). Concrete tokens (spacing and type scales, palette values, icon set, motion
  durations), the component set and the drop-zone status-surface design are chosen at planning, using the existing
  toolkit if the product has one. A new dependency is a candidate only after a fit check in the target build.
