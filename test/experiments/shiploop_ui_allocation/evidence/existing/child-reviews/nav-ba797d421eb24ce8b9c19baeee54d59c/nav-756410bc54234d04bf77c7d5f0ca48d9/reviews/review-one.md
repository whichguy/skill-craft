# Research Improve review 1

## Candidate, authority, and history

- Candidate: `<study>/existing/run/notes/research.md`, its pending research result, and the related environment note.
- Product baseline remains tracked `main` at `8f318f0adb98cb3a6e9c6419e57e48ef96ef2a8e`. This child may correct only run-local research/result evidence and child artifacts; it has no product, API, target, install, commit, or deployment authority.
- `history-review-one.txt` records the sole fixture commit. One independent read-only reviewer was already used by the intake child, so this review records the permitted self-review limitation.

## Material finding and correction

**R-REV-01 — export notification scope/cursor semantics were absent.** The export contract supplies account-authorized collection statuses and monotonic revisions, but it does not choose the active client collection or notification-comparison state. Current client source has no export endpoint/component/collection binding; observed account switching aborts note work only. Treating feasibility as sufficient without this distinction risks a stale/repeated or wrong-account notice.

Applied correction: added Q-R2a to the run-local research note. It keeps the existing visible-poll/foreground feasibility result, but records account/collection/cursor and identity/lifecycle reset as an open **specification** decision. It expressly does not select persistent notification history, a new API, storage carrier, or transport.

## Rechecks and retained limits

- `export-scope-contract-review-one.txt` and `export-client-gap-review-one.txt` support the finding from current API/platform/client evidence.
- `research-artifact-check-review-one.txt` validates the updated seven-question frontier, all source/evidence locators, and explicit authority boundaries.
- `source-hash-review-one.txt`, `source-hash-after-correction.txt`, `tracked-status-review-one.txt`, and `tracked-diff-review-one.txt` show all tracked product sources remain unchanged.
- Current controlled facts and their limits remain unchanged: no client persistence/draft API/WebSocket/server runtime, no real target/deployment access, inferred note API semantics, and no behavioral harness/full suite. These are disclosed downstream gates, not solved by this record correction.

This is a **non-trivial** review because it changes the research frontier and downstream specification decision. Two further distinct trivial reviews with current checks are required.
