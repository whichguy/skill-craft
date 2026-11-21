# Architecture: Admin Console, User Administration

How the product is built, apart from what it must do (`spec.md`). Written at the spec stage with no repository to
inspect, so every entry below is **proposed** and carries the observation that would confirm or overturn it.

## Stack

Unknown: language, framework, store and hosting platform are not yet observed (spec G-1, G-3). No dependency is
chosen here. Runtime versions and working commands belong in `environment.md` once discovered.

## Structure

Proposed units, named by responsibility only (to be mapped onto the real modules at plan):

- an **import boundary** that accepts the multipart request, enforces the byte limit while reading, and maps outcomes
  to the response of spec R-8;
- a **pure CSV import core** (decode, parse, header check, row validation, normalisation, error gathering) with no
  I/O, so the rules of spec R-2 to R-6 and R-8 are testable without a product;
- a **commit step** that creates all users in one transaction through the product's existing user-creation path
  (spec R-7, R-12), and an **audit step** (spec R-10).

## Conventions

none yet: inherit the repository's conventions once discovered.

## Interfaces and boundaries

- Browser to import endpoint (AD-3). Endpoint to user store, audit trail and onboarding mechanism: existing
  internal boundaries, not new services.
- Reuse the existing single-user creation path for each row rather than duplicating its rules (spec R-12).

## Real-boundary checks

A local test cannot prove: the hosting platform's request limits (owner: plan, platform discovery; spec G-3); the
store's transaction and unique-constraint behaviour at 5,000 rows (owner: test stage; G-7); real onboarding message
delivery (owner: product-acceptance; R-12); real spreadsheet exports (owner: a tester; R-17.2).

## Decisions

### AD-1: Process the import synchronously in the request

- **Choice:** validate and commit within the one request; the response is the completion.
- **Why:** at most 5,000 rows keeps one commit small, and it needs no job store, worker or recovery owner.
- **Alternatives:** an asynchronous job with a durable operation record and polling (needs a processor and a
  recovery owner; spec `Service boundary contracts` lists what that would add).
- **Status:** proposed. **Revalidate when:** the timed FX-17a run (spec R-15.1) approaches or exceeds the platform
  limit, or the platform is found to lack a request limit that fits.

### AD-2: Use the stack's maintained CSV parser, configured strictly

- **Choice:** do not hand-split lines; configure a maintained parser for RFC 4180 quoting with strict failure on a
  bare quote, a lone CR or an unterminated quote, and with a field-size guard.
- **Why:** quoting rules (embedded commas, doubled quotes, line breaks in quotes) are where hand-rolled splitting
  fails, and spec R-2.2 and R-5.2 require exact outcomes.
- **Alternatives:** a hand-written parser (rejected: more risk, no benefit); a lenient parser mode (rejected: the
  spec requires `malformed_csv`).
- **Status:** proposed, parser unnamed until the stack is known. **Revalidate when:** the chosen parser cannot
  report the record number or reject a bare quote.

### AD-3: One HTTP operation, `multipart/form-data`, file part `file`

- **Choice:** `POST /api/admin/user-imports` (path proposed; follow the repository's route convention if one
  exists), JSON response per spec R-8, status codes 201, 401, 403, 413, 422, 500.
- **Why:** the UI and any script share one contract; the spec's API surface is this operation.
- **Alternatives:** a form post returning a rendered page only (rejected: not observable by a headless consumer).
- **Status:** proposed. **Revalidate when:** the repository's API conventions are seen (spec G-1).

### AD-4: Enforce email uniqueness in the store, not only by pre-check

- **Choice:** a unique constraint on the lower-cased email, plus the pre-check of spec R-6; a violation at commit
  rolls the transaction back.
- **Why:** spec R-9 requires two racing imports not to both create one address; a read before the write cannot
  guarantee that.
- **Alternatives:** an application-level lock (rejected: does not protect other writers such as single-user
  creation); serialising all imports (rejected: does not protect against other writers either).
- **Status:** proposed and **unresolved** until the store is known to support a case-insensitive unique constraint
  and a transaction of 5,000 inserts (spec G-7). If it cannot, that is a spec-level conflict, not an architecture
  workaround.

## Superseded

none.
