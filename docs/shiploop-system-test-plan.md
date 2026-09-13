# ShipLoop system-test sequencing plan

Status: implemented and validated; regression closeout below. Native Backchain dependency
analysis, not a scheduler-certified Backchain package. Scope: ShipLoop only;
unrelated Review Coverage work remains untouched.

## Outcome and dependency analysis

System-test requirements survive context resets, accumulate cross-step needs,
and become executable DAG activities before or after the authorized deployment.
Existing step contracts, test runner, improvement loops and receipts remain the
execution engine. No additional scheduler, external integration or authority.

Observed initial facts: the DAG supplies prerequisite scheduling; contract tests
require real verify-record checks; outer quality forbids direct product/test
edits; outer publication records host-reported smoke evidence, not an executable
test-authoring loop. Therefore real post-deployment test work must follow an
explicit DAG publication, not be attached as a prose promise to outer publish.

```mermaid
flowchart LR
  R[Global requirements] --> I[Implementation prerequisites]
  I --> PRE[Author and verify pre tests]
  PRE --> D[Authorized DAG deployment]
  D --> POST[Author and verify post tests]
  POST --> Q[Global quality reconciliation]
  Q --> H[Evidence and handoff]
```

## Forward plan, backchained prerequisites, and validation

1. S1 — Validate the bounded global catalog and graph. Needs existing contract
   and dependency semantics. Produce stable case IDs, phase decisions, expected
   outcomes, environment references, prerequisite IDs and executable owners.
2. S2 — Bind catalog acceptance/revision to existing Markdown transactions.
   Needs S1. Produce a derived global document, cold-context reader, explicit
   iteration reassessment and final receipt reconciliation. New runs require
   the catalog; legacy absence is not retrospective certification.
3. S3 — Explain the phases in packets, reference material and README. Needs S1's
   field contract and S2's actual callbacks. Produce accurate path references,
   author/refine/run/fix instructions and pending-only replan guidance.
4. S4 — Verify executable outcomes and negative boundaries. Needs S1–S3.
   Produce native unit and protocol tests, pinned regression results, review
   findings/fixes and synchronized plugin view. Commit only scoped changes.

Backward audit: completion needs actual passed contract checks, which need
authored tests and a reachable target, which need completed implementation and
(post-deployment only) deployment prerequisites. Missing access is blocked, not
N/A. Test corrections need independent requirement evidence, not weaker
assertions. Production/fuzz/destructive checks still require authorization.
New discoveries use existing knowledge/outer-work journals and pending replans;
those records never count as passing test evidence.

## Acceptance tests

- Valid fan-in → pre-test → deployment → post-test graph is accepted.
- Missing prerequisites, wrong order, absent deployment, orphan cases/test
  steps, wrong contract IDs/outcomes, and malformed catalogs are rejected.
- No-deployment projects can require integrated pre-release tests and explain
  post-deployment N/A. Required post-deployment tests reject outer-loop publish.
- Catalog updates cannot erase or mutate obligations whose test/deployment
  step is running or complete; new corrective steps retain prior evidence.
- Every carry-forward/post-inner checkpoint records a global-test assessment.
- Cold context uses current authoritative plan data, not an edited/stale view.
- Final quality rejects missing, failed or changed system-test proof.
- Existing local step tests and embedded two-trivial-pass Until loops remain
  mandatory; global tests do not postpone required local verification.

## Evidence-first decision

Adopt existing DAG/contract machinery plus a small typed catalog. Defer a new
outer test executor: it would duplicate authoring, repair and authority rules.
Pre-release tests cannot establish all production behavior; controlled
post-deployment checks are separately justified by environment and risk. See
[Google SRE canarying releases](https://sre.google/workbook/canarying-releases/).
Select integrated journeys where needed, without turning every check into a
large end-to-end test; see [Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html).

## Implemented result and review learnings

- The accepted Markdown DAG owns the catalog. Its generated requirements view
  has a cold-context reader that reconstructs current data from the authority,
  not from a potentially stale view. New runs require explicit phase decisions;
  old runs are compatible without retrospective certification.
- Pre/post system-test activities are ordinary prerequisite-scheduled steps.
  They reuse Ready/Done contracts, author/refine/run/fix behavior, fresh lint and
  test gates, embedded Until improvement, learning commits and merge receipts.
- Carry-forward, post-inner and quality require a structured reassessment.
  Declared future needs survive in a bounded pending-ID queue and the knowledge
  ledger. Replanning must map each queued ID to a changed/new case and pending
  typed test owner. Unrelated work or a prose mention cannot close the need.
- Review exposed an important distinction: completed test certificates prove
  their saved execution epoch, not a later environment. Audit their historical
  integrity without invalidating them merely because later knowledge exists;
  changed requirements need corrective test cases and newly completed evidence.
- The README, phase reference, action packets and HTML report explain the same
  catalog, readers, authority and safety boundary. No second test executor,
  external integration or generic remote-attestation string was introduced.

## Validation closeout

The regression sweep used isolated detached snapshots and an alternate Git
index so unrelated working changes could not enter test baselines. Final
test-only fixture repairs were checked in the main checkout against the same
unchanged runtime as `fd3ee99`; only scoped ShipLoop changes were staged. The
results below are revision-specific, not a claim that one final umbrella command
passed uninterrupted.

| Check | Evidence and outcome |
|---|---|
| Full native regression coverage | Snapshot `74298a5`: 471 tests across all 43 native suites (action-walk split into three disjoint shards). Two failures: cold packet length and an old direct-call knowledge fixture missing the new assessment field. Other 469 tests passed. |
| Final runtime and report closeout | Snapshot `fd3ee99`: 165 tests across 13 relevant suites passed, including all 24 new catalog/protocol/report tests, packet/reference routing, Until, contracts, report and artifact consumers. |
| Cold planning repair | Snapshot `fd3ee99`: `PlanningLoopTests.test_cold_context_repair_revisit_and_old_run_safety` passed with the unchanged 7,000-character budget. Removed redundant shared-directory wording, not orientation or safety requirements. |
| Cold step planning | Snapshot `1d21bc3`: `StepPlanningCliTests.test_initial_step_plan_is_repeatable_cold_and_gates_implementation` passed separately. Full 17-test step-planning suite also passed at `74298a5`. |
| Actual CLI integration | Snapshot `1d21bc3`: full delivery/action-history/terminal-journal walk and outer corrective-pending-step walk passed (2 tests). The fixture schedules `SYS-INTEGRATED-001` on `S2` only after `S1`, with executable `T-S2` contract evidence. |
| Knowledge fixture repair | The final exact `ShipLoopKnowledgeTests.test_carry_forward_checkpoint_is_cold_readable_and_fail_closed` rerun passed in 100.446 seconds (exit 0) in the main checkout. Direct completion fixtures now supply the required assessment while preserving both credential-secret rejection assertions. The other three knowledge tests passed in the full sweep. |
| Orientation fixture repair | A final reviewer found the shortened packet wording left one stale literal assertion (13/14 at `fd3ee99`). The repaired test asserts the exact absolute guidance root and retains required file/heading checks. All 31 orientation, orientation-context, actual-CLI orientation and reference-routing tests passed in the main checkout. |
| Independent review | Historical-proof and pending-mapping findings were corrected and re-reviewed. The final narrow re-review is clean after the orientation assertion repair; focused protocol and orientation tests passed. |
| Static and distribution checks | Scoped Ruff, native skill frontmatter (17 skills), shell syntax, plugin-view parity and whitespace checks passed. Four touched Markdown documents have balanced fences and 102 resolvable local links; diagrams were not visually rendered in this run. |

Snapshot logs remain under `/tmp/shiploop-system-tests-validation.KYmaPU/`;
final main-checkout results are in the task's tool transcript. Interrupted or
uncollected harness attempts are not counted as passes. These are
local development tests; no live deployment, production test, or remote target
certification was performed. Runtime evidence proves ordering and recorded
checks, not exhaustive coverage or semantic correctness of remote assertions.
