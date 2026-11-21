# User Administration: architecture decisions

Written by the spec stage run on its own. No repository, runtime or existing architecture was available, so every decision is
**proposed** and stack-neutral; binding to a framework waits for environment discovery (G-6 in `spec.md`). Requirements live in
`spec.md` (R-n); this file holds only structure and technology choices.

## Decisions

### AD-1 Two consumer surfaces over one HTTP import operation
- Status: proposed. Serves: R-1, R-2, R-7, R-11.
- Import API: one operation, a `multipart/form-data` POST with a single file part named `file`, at `POST /admin/users/import`
  (path is a default; align with the existing routing scheme, G-6). It returns JSON with the R-7 body.
- Status mapping: 201 `created`; 422 `rejected` for any file-level error except size, or any row error; 413 `rejected` with
  `file_too_large`; 400 `rejected` with `no_file`; 401 unauthenticated; 403 not an admin (also when demoted before commit);
  500 `failed` with `import_id`. The body shape is the R-7 shape in every 2xx/4xx-after-authorisation case except 401/403, which
  use the application's existing error shape.
- Import page: a browser page in the admin area that calls the Import API and is the only consumer built here. The API is
  also the contract for scripted callers.
- Alternatives considered: server-rendered form post (rejected: weaker progress and unknown-outcome feedback in R-11);
  a job-based API (rejected, AD-2).
- Evidence limits: no existing route or auth scheme was read. Revalidate when G-6 is resolved.

### AD-2 Synchronous, bounded processing; no job queue
- Status: proposed, conditional on G-1. Serves: R-2, R-6, R-7, NFR-6, NFR-7, NFR-8.
- The request is parsed, validated and committed inside the single request, and the response is the final outcome. The file
  is bounded by `max_bytes` and `max_rows` (configured; defaults unresolved, G-1), the body is read as a stream and cut off
  once `max_bytes` is exceeded, and processing is single-pass.
- Why: the request names no volume; a bound makes the work short; a queue would add accepted-but-unprocessed work, worker
  crash recovery and result polling that nothing requires.
- Revalidation trigger: if G-1 sets limits whose worst-case run time exceeds the hosting platform's request limit (unknown
  here), reopen this decision before adopting the limits; the alternative is an asynchronous operation with a durable
  status record, which would change R-7 and R-11 and needs its own contract (acceptance durability, worker authority,
  recovery of abandoned work).
- Evidence limits: no platform documentation or probe was available.

### AD-3 Atomic commit on the existing user store, with uniqueness enforced by the store
- Status: proposed. Serves: R-5, R-6, R-8, R-9, NFR-5, NFR-13.
- Validation runs in memory first (R-3 to R-5, including a read of which of the file's emails already exist), then one
  transaction inserts all users and the audit record (R-9) and re-checks the admin role (R-1). A unique constraint (or
  equivalent) on the normalised email makes the store the arbiter of races; a constraint violation inside the transaction rolls
  everything back and is reported as `already_exists` on the conflicting rows. A transaction-less store is not acceptable
  without an equivalent all-or-nothing mechanism (unknown, G-4).
- Test seams (NFR-13): a pause point between validation and commit and fault injection at the store and audit boundaries, in
  test configuration only.
- Alternatives considered: per-row inserts with compensating deletes (rejected: not atomic, leaves a visible partial set);
  application-level locking (rejected: does not cover other writers of the user store).
- Evidence limits: the store engine, its transaction support and any existing unique index are unknown (G-3, G-4).

### AD-4 Uploaded data is held only in the request
- Status: proposed. Serves: R-10, NFR-4.
- The file is parsed from the request stream/memory and is not written to the store, object storage or a cache. If the
  platform's multipart handler spools to a temp file, that file is deleted in a guaranteed cleanup path. Log and audit
  writers receive counts and codes only, never row values.
- Evidence limits: whether the target platform spools uploads is unknown.

## Not decided here
- The concrete UI toolkit, tokens and component build for the Import page (premises: spec `Interaction and lifecycle` and
  NFR-12; the plan records the concrete UI direction once G-6 is known).
- Choice of language, framework, store engine and hosting: no input exists.
