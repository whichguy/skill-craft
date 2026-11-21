# User Administration — Architecture

How the product is built. What it must do lives in `spec.md`; this file holds structure and technology decisions only
(`AD-<n>`). No repository, stack, runtime or hosting platform was available when these were written, so every decision
below is a **proposed default** (status `proposed`) that the plan must revalidate against the real repository before
relying on it. Nothing here has been built or tested.

## Stack

Unresolved. Language, web framework, user store, session mechanism and UI toolkit are whatever the existing product
already uses (spec `G-1`). No new dependency is chosen here; a CSV parser is a candidate only where the existing stack
lacks one, and then must be checked against the quoting, BOM and strict-malformation rules of `R-2`.

## Decisions

### AD-1 One synchronous request does the whole import
- Status: proposed. Serves R-2, R-4, R-5.
- Decision: the upload request parses, validates and commits, and its response carries the final outcome. No background
  job, queue or polling endpoint.
- Why: the file is bounded by the configured row and byte limits (R-2), so the work is bounded; a synchronous outcome
  keeps "accepted" and "done" the same fact, so the UI never shows an unconfirmed state.
- Rejected: an asynchronous job with a status endpoint. It adds a processor, recovery owner and status retention for no
  demonstrated need.
- Revalidate when: the production limits (spec G-3) are chosen and a worst-case file would not finish inside the
  platform's request timeout (unknown); then the async contract of the service-discovery guide applies.

### AD-2 All-or-nothing commit by one store transaction; uniqueness enforced by the store
- Status: proposed. Serves R-4, R-6, R-11.
- Decision: all inserts of one import run in one transaction. Uniqueness of the normalized email is enforced by the
  user store itself (a unique constraint or an equivalent atomic conditional insert). The validation-time existence
  check (spec R-3) is advisory and gives readable errors; it is not the guard. A uniqueness conflict at commit rolls the
  transaction back and the import re-runs the R-3 existence check to build its 422 report.
- Prerequisite (open): the existing store must offer a multi-row transaction and a unique guarantee on the normalized
  email. If it does not, the plan raises it before R-4 and R-6 are scheduled; a check-then-insert without a guard would
  fail R-6.1.
- Rejected: per-row inserts with compensation deletes (a crash between inserts leaves partial state); an advisory lock
  around the whole import (does not protect single-user creation paths that write outside the import).

### AD-3 No import record is kept; upload bytes live only for the request
- Status: proposed. Serves R-8, R-7.8.
- Decision: no table or file of past imports. The request body is read with a hard byte cap (the configured
  maximum, `max_bytes + 1` bytes read at most) into memory, or a temp file that is removed on every exit path. Parsed
  rows exist as a bounded in-memory list (bounded by `max_rows`). The report goes out in the response only.
- Why: no requirement asks for import history; every retained copy of the file is retained personal data (R-8.2).
- Revalidate when: a requirement for import history or re-download of a report is added.

### AD-4 Authority is re-read on each request
- Status: proposed. Serves R-1.
- Decision: the server derives "is admin" from the current user record on every import request. Page-load state and
  any role claim cached in the client or session are not trusted. The page and the operation share one check.
  Anti-forgery protection follows the product's existing session mechanism (R-9).

### AD-5 UI extends the existing UI stack
- Status: proposed. Serves R-7, R-12, R-13.
- Decision: the import page is built with the product's existing UI toolkit, tokens and component primitives. Only if
  the product has none (spec G-1) does the plan choose a toolkit, recording exact package and version, and evaluates it
  against the product's build and hosting.
- Component premises: file-drop zone (native `input[type=file]` underneath, so keyboard and screen-reader behaviour is
  native), file chip, primary action button with busy state, live status region, result summary, problems table that
  reflows to stacked rows on narrow widths.
- Interaction premises: one request in flight; draft (chosen file) separate from request state separate from accepted
  result; the result is replaced only by the next submit.
- Skin premises: see R-12 for the named visual reference and starting appearance; the plan records the concrete tokens
  (type scale, spacing scale, palette for light and dark, radii, motion durations) in this file as an AD when it
  chooses them.

### AD-6 Observability reuses the existing audit and log facility
- Status: proposed (unresolved, spec G-1/G-4). Serves R-8.3.
- Decision: one audit event per import attempt written through whatever audit or structured-logging facility the product
  already has; a new sink is created only if none exists. Events carry actor id, outcome, counts and byte size, never
  row contents.
