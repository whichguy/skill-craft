# Release transition guidance

## Outcome and scope

Make global deployment work explicit within the existing outer stages: plan its
dependencies and execution owner, verify readiness, perform authorized effects,
observe completion, and verify the resulting consumer state. Keep the Navigator
stage graph and standalone Improve ownership unchanged.

The September 18 experiment series (`shiploop-outer-transitions-20260918-100237`)
found that existing Navigator persistence survived cold recovery and stale
callbacks (seven checks). A separate SQLite fault lab exercised 14 scenarios plus
a request-key conflict extension, with nine tests and 100 state/outcome checks.
Provider lookup recovered a lost receipt; cursor-only recovery blocked ambiguity;
a conditional target write rejected a competing release. These are fixture
results, not proof of real provider behavior.

Ten model decision trials did not establish a benefit for wholesale prompt
expansion. Both variants missed a different judged criterion. The longer variant
omitted final local candidate/evidence checks when deployment was non-applicable;
the baseline left a write-time concurrency guard implicit in one recovery case.
Judges disagreed on the latter's severity. Implement narrow guidance, and verify
it with fresh decisions as well as deterministic routing tests.

## Changes

1. Add a focused `Release operation ownership` section to the existing environment
   guide. Retain per-operation intent, dependencies, authority, candidate/target,
   observed outcome and recovery limits in current notes/evidence references.
   A request ID alone does not create provider idempotency or target exclusion.
2. Route that section directly to release planning, readiness, execution and
   verification, including their existing Improve handoffs after cold recovery.
   Clarify acceptance versus terminal completion and resulting-state verification.
3. Preserve current local candidate and consumer evidence checks when external
   deployment is non-applicable. Improve inherits the parent's effect boundary;
   reviewing a plan/check does not execute deployment or replay an earlier effect.
4. Correct references that conflate Navigator v3 with legacy `outer-improve` or
   the managed/legacy `outer-work` journal.
5. Generate plugin views from skill sources and validate routing, existing delivery
   gates, and fresh model decisions. Keep experiment/runtime artifacts outside the
   product checkout.
6. Preserve the actual stage order: `release` verifies operation postconditions,
   returns through standalone Improve, then `release-verify` observes final
   consumer behavior. Unmet earlier deployment/testing prerequisites use the
   existing outer `replan` route; the host cannot schedule an earlier stage itself.

## Deferred machinery

No new SDLC stage, state schema, operation scheduler, automatic compensation,
polling loop or Improve counter is justified by these experiments. Prefer a
verified existing release runner when it durably owns the complete operation
sequence. If a real compound deployment has no such owner, assess a small
script-owned operation cursor separately. The current Navigator does not own
individual sub-operations inside `release`; prose must not claim otherwise.

A future cursor pilot first needs an actual deployment inventory: each operation,
dependency, exact target/authority, job identity, terminal observation, supported
retry/reconciliation behavior, and concurrency protection. A generic CI success
receipt does not establish those guarantees or consumer behavior.

## Verification and completion criteria

- A cold producer or pending Improve packet for each affected stage supplies the
  correct reference locator without changing its parent action or child binding.
- Partial release evidence remains recoverable after blocked/resume; no new graph
  transition or remote-effect claim is introduced.
- Existing local-only consumer obligations, stale-observation rejection and
  standalone Improve transition tests remain green.
- Fresh isolated model decisions cover local-only delivery, lost acknowledgment,
  failed asynchronous work, mixed consumers and missing provider guarantees.
  Evaluate observable decisions, not phrase matching; no live effects or synthetic
  receipts count as real Improve execution.
- Source checks, generated package checks, an independent review and a real
  standalone Improve run establish the final bounded candidate. Retain actual
  evidence separately; do not claim unrun provider integration or publication.

## Implementation evidence

The cold-routing regression was observed failing before the new route was wired,
then passed for all four release stages, their pending Improve handoffs, and
blocked/resumed partial release evidence. The final focused run passed 70 tests:
12 guidance, eight reference-routing, 21 Navigator v3, and 29 delivery-contract
tests. Generated ShipLoop parity, portable-skill hygiene and diff checks passed.

Preserved model trials exposed two stage-boundary ambiguities: final consumer
verification could be pulled before release Improve, and missing staging/test
work could be described as though the host could revisit earlier stages itself.
The explicit boundaries in change 6 address those findings. These decisions are
hypothetical prompt interpretation, not live provider validation.

The first implementation trial batch mistakenly supplied both a producer and its
future Improve prompt. That contradicts the current action and is excluded from
producer-stage acceptance evidence. Fresh producer-only trials retain the original
criteria; the fixture README records this methodological constraint. Raw inputs,
responses, judgments and checks are retained outside the checkout in the
`shiploop-outer-transitions-20260918-100237/implementation-validation` experiment.
