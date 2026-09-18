# Discovery Improve review 1

## Candidate, authority, and history

- Candidate: `<study>/existing/run/notes/discovery.md`, `<study>/existing/run/notes/environment-lifecycle.md`, and the pending discovery result.
- Product baseline remains clean tracked `main` at `8f318f0adb98cb3a6e9c6419e57e48ef96ef2a8e`. This review has no authority to edit product source/tests/configuration, install/provision/deploy, or commit.
- Re-read reachable history in `history-review-one.txt`: one fixture commit. It informs scope only.
- Independent-review limitation: one read-only independent review was used by the preceding intake child; this discovery child performs a recorded self-review under the parent’s one-review limit.

## Material finding and correction

**D-REV-01 — broken run-note evidence locators.** Both discovery/environment notes used `../evidence/...`, which resolves under `run/evidence/` rather than this case’s `<study>/existing/evidence/`. That would break cold recovery even though the raw evidence exists.

Plan: correct only the affected run-note locator prefixes to `../../evidence/...`, then prove each referenced evidence file resolves from `run/notes/`. No product artifact or parent result decision changes.

Applied correction: updated the two discovery-stage run notes. `run-note-locator-check-review-one.txt` confirms all eleven referenced local evidence files resolve after the correction.

## Rechecks and retained decisions

- `smoke-review-one.stdout`/`stderr` and `smoke-after-correction.stdout`/`stderr`: `node --check app.js` passed; it remains syntax-only, not behavioral coverage.
- `probe-review-one.json` and `probe-after-correction.json`: controlled v2 facts remain unchanged (no client persistence, no draft API, no WebSocket/server runtime; not live deployment evidence).
- `source-hash-review-one.txt` and `source-hash-after-correction.txt`: frozen tracked product sources remain `OK`.
- `tracked-status-review-one.txt`, `tracked-diff-review-one.txt`, `tracked-status-after-correction.txt`, and `tracked-diff-after-correction.txt`: no tracked product changes/diff.
- The lack of a behavioral harness/full suite, an actual note API contract, a remote delivery route, and a compatible draft carrier remain accurately recorded research/planning gaps. They are not repaired or marked N/A by this review.

This is a **non-trivial** review because it corrected durable evidence recovery paths. Two further distinct trivial reviews with fresh checks are required by the runtime gate.
