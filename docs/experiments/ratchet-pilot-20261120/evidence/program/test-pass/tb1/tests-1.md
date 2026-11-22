## Failing now

- C-34 — The service started with a saved 65-letter assignee. It rejected the numeric and empty-string cases with record-specific diagnostics.
- C-44 — `npm test` ran the new assignment tests, but they had no case checking assignee visibility in the human-readable CLI listing.
- C-45 — A blocked save returned 500 `internal` while the running service showed Lee as the owner, advanced the update time, appended an audit entry, and queued a notice for Lee. After storage was restored, an unrelated successful save persisted the failed reassignment.

## Discoveries

- Specify how surrounding whitespace is handled across an assignment PUT and an assignee filter | Observable: Assign Dana, then repeat with `" Dana "` and query with `assignee=%20Dana%20` | Why: The padded PUT was a successful no-op, while the padded filter returned no tickets and the plain filter returned the assigned ticket.
- A cursor resumes after the last returned ticket ID against the current matches when assignments change between pages | Observable: Read one Dana ticket, reassign it to Lee, assign a higher-ID ticket to Dana, then follow the first cursor with the Dana filter | Why: The next page included the newly matching ticket even though the ticket that supplied the cursor no longer matched.

## Checks nothing here can break

- C-8 fails if an assignment to a missing ID returns success or if its 404 has an error code other than `not_found`. Both faults were verified on isolated copies with missing IDs in a populated data file. The starting product's unknown-route response is also 404 `not_found`. The failing original test and the supplied source faults do not alter that response. C-1 and C-3 detect an absent assignment route by exercising it on an existing ticket.

## Faults that change nothing

- `src/app.js:16` (`false` to `true`) changes the fallback for an omitted `logRequests` argument. The service entry point always supplies a boolean derived from `LOG_REQUESTS`, including `false` when the variable is unset. The fallback is unreachable through the supported entry points.

## Verified regression checks

- `R-cli-table` caught both edits at `src/format.js:36`. The `!==` edit moved short values out from under their headers. The `+` edit added trailing padding after shorter titles.
- `R-data-file` caught all seven persistence edits. The refused fixtures cover a reused next event ID (line 92), separately missing audit delta fields (both edits at line 160), invalid attempt counts (line 170), non-object event data (both edits at line 180), and invalid next event IDs (line 194).
- C-43 reports execution evidence for all 17 original test files on the build. It also fails the original-byte check on an isolated copy with a failing case added to `test/api.test.js`.
