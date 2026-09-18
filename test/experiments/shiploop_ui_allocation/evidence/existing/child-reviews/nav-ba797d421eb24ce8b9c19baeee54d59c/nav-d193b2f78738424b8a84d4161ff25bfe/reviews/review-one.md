# Spec Improve review 1

## Candidate, authority, and history

- Candidate: `<study>/existing/run/notes/spec.md`, related research/environment notes, and pending spec result.
- Product baseline remains tracked `main` at `8f318f0adb98cb3a6e9c6419e57e48ef96ef2a8e`. This child may correct run-local spec/result evidence only; it has no product/API/target/install/commit/deployment/standalone-Backchain authority.
- `history-review-one.txt` records the reachable fixture history. One independent read-only review was consumed by the intake child; this child records the permitted self-review limitation.

## Material finding and correction

**S-REV-01 — reload recovery conflated distinct outcomes.** The original state diagram modeled reload as `Pending → Restored` and F-1 did not distinguish an authorized draft, an authorized absence, and a carrier read failure. That could make a failed recovery appear equivalent to no draft or a restored pending draft.

Applied correction: the conditional recovery flow now starts with `RecoveryCheck`, branches to `Restored`, `Confirmed`, or `RecoveryUnavailable`, and documents the three corresponding outcomes in F-1 and T-5. The carrier remains entirely unselected and Q-R1/Q-R3 remain blockers; the change only prevents a false behavior claim.

## Rechecks and retained limits

- `recovery-contract-review-one.txt` and `recovery-model-gap-review-one.txt` support the finding against the current export/platform/client evidence and pre-correction candidate.
- `spec-artifact-check-review-one.txt` validates the revised recovery branches, identifiers, locators, embedded Backchain mode, and unresolved prerequisite language.
- `source-hash-review-one.txt`, `source-hash-after-correction.txt`, `tracked-status-review-one.txt`, and `tracked-diff-review-one.txt` show all product sources remain unchanged.
- Current controlled limits are unchanged: no client persistence/draft API/WebSocket/server runtime, no real target/deployment access, no owned note API contract, and no behavioral harness. No carrier, endpoint, target, dependency, or test result was selected or claimed.

This is a **non-trivial** review because it changes a high-risk recovery/state transition. Two further distinct trivial reviews with current checks are required.
