# Specification

## Requirements

### R-1: Filter listing
Basis: request S2–S3, S7. GET /users filters names by case-insensitive literal substring; absent or empty name includes every user; unmatched text returns empty array. Without page or size, response remains an ID-ordered JSON array; unknown query parameters are ignored. Confirm by HTTP node:test cases including case, metacharacters, empty and unmatched values.

### R-2: Paginate listing
Basis: request S4–S5. Either pagination parameter produces JSON object page, size, total, pages and items. Page is 1-based, default 1; size defaults to 10. Filter precedes count and slice, ordered by ID; pages is ceiling of total/size, zero for no matches; out-of-range items empty. Confirm by HTTP tests for defaults, partial page, filtered counts, empty and out-of-range.

### R-3: Validate pagination
Basis: request S6. page is a whole number >=1, size is whole number 1..100; empty or invalid input yields HTTP 400 JSON error describing the offending parameter. Confirm by HTTP tests covering bounds, empty, nonnumeric and fractional inputs.

### R-4: Preserve existing behavior
Basis: request S1, S7–S9. GET /users/:id and existing behavior remain unchanged; existing tests remain unchanged and pass alongside new node:test cases under test/ using npm test. Confirm full suite and direct HTTP compatibility cases.

Data remains process-local and read-only as before, with process lifetime and no identity, persistence, cache or asynchronous service change. No user state is mutated by a listing request.

## Non-functional requirements
Node >=20 and no npm dependencies are preserved; confirm package manifest and npm test. No new performance, deployment or availability bounds requested; no external services involved.

## Retired
None.
