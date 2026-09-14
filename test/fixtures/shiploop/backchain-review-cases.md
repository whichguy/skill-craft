# Backchain guidance interpretation controls

These are read-only model-comprehension probes, not runtime tests or proof of
planning reliability. Give a fresh reviewer one **Input** and the current
packet-selected sections of `references/backchain-planning.md` and
`references/execution-planning.md`. Do not provide the **Expected distinctions**.
Ask what action result, planned work/checks, unresolved issues and callback
boundary it infers. Compare its answer to the independent input, not merely to
the requirements the model chooses to list. Do not initialize a run or perform
the proposed work. Preserve failed/ambiguous results rather than silently
excluding a case. The deterministic companion is
`test/shiploop-backchain-guidance.test.py`; it tests routing, not these meanings.

## A — Missing independent outcome

**Input:** Sequence objective review. Request: CSV export returns all selected
records, each export leaves an audit entry, and use judgement to keep the code
readable. Candidate: S1 exporter, S2 export-content tests. Final acceptance is
"export tests pass."

**Expected distinctions:** Missing audit behavior/observation is material despite
content tests. Retain readability as scoped work/review, not a fabricated taste
test. Each measurable outcome needs its own case/observation; shared work is
allowed when prerequisites align. A review callback is not implementation or
test-pass evidence. Do not quietly replace the original request with CSV-only
acceptance.

## B — Constructible fixture, not assumed state

**Input:** Initial step-plan. Approved objective tests that local OAuth login
maps to the correct local user. A user model can store provider IDs and local
mock OAuth endpoints exist, but the isolated test DB is empty. Disposable local
fixture data is authorized; modifying any live production environment is not.

**Expected distinctions:** Capability/mock endpoints do not supply a matching
record. Plan an isolated matching-user fixture and cleanup before the exact
identity assertion; inspect real contracts rather than inventing them. Do not
ask for production access to create a permitted local fixture. Planning does
not create the fixture or claim the future test passed. Source changes remain
within the selected step's approved scope, not implied by missing data.

## C — Invalidated clock and missing negative case

**Input:** Sequence objective review. Remove legacy handling only after all
writers use the new format continuously for 12 hours. Invalid new-format
payloads must not fall back to legacy. Candidate removes legacy 12 hours after
deployment. Deployment was 20 hours ago; a rollback resumed legacy writes
3 hours ago and no later restoration is evidenced. No test covers fallback.

**Expected distinctions:** The deployment timestamp does not establish the
qualifying interval. Reestablish all entry conditions, then require a complete
continuously-valid window with invalidation/restart evidence. Retain a distinct
invalid-new-format case proving legacy fallback is not invoked. Missing writer
inventory/current state remains unresolved; a deployment receipt or complete
blocker report is not permission to remove legacy handling.

## D — No invented work control

**Input:** Step-plan review. Approved task only fixes a misspelling in a README
heading. Candidate changes the word, verifies the intended text and surrounding
link anchor, runs the already-required documentation lint and records review.
No code, runtime, external access or migration is implicated.

**Expected distinctions:** A clean review is legitimate if inspection supports
the candidate. Do not add migrations, infrastructure, mock data or extra DAG
nodes merely to fill the policy's categories. Existing required checks and
evidence still apply; one review callback is not two converged review cycles.
