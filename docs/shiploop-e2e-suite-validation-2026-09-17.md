# ShipLoop full-suite implementation and validation

The full local apparatus is implemented for nine one-shot requests: create,
feature, and refinement for tic-tac-toe, Checkers, and Battleship. The
[full plan — scope and experiment matrix](shiploop-e2e-full-suite-plan-2026-09-17.md)
describes readiness, completion criteria, the experiment matrix, and deferred
hosted delivery. The
[harness README — commands and evidence contracts](../test/experiments/shiploop_e2e/README.md)
documents usage.

## What was implemented

- Six live suites: launch and planning prefixes; each three-case game chain;
  and all nine cases. At the recorded checkpoint, Grok defaulted to `xhigh`,
  4800 seconds, and 1000 turns. The subsequent user-requested default is
  7200 seconds (two hours) for future requests; historical receipts retain their
  original limits.
- Create cases require a physically empty folder and execute there as the real
  CWD. Feature cases execute in the original product repository. Fresh processes
  inspect and fingerprint the selected skill again for every request.
- Independent game oracles, cumulative before/after replays, absent-to-present
  eligibility, source continuity review, and GAS source-closure checks.
- Driver provenance, bounded execution, exact request/repository/schema binding,
  minimal inherited environment, product-external review material, and evidence
  hashes. External adapters remain trusted code, not a security sandbox.
- Workflow review inventories for every selected test and Improve action;
  campaign accounting retains failures, missing cases, and comparison limits.
- Four focused no-model groups plus `all`; captured real-shell regressions and
  guards against stale run reuse, source drift, and unsupported lifecycle claims.

## Executed checks

| Experiment | Observed result | Scope |
| --- | --- | --- |
| Complete apparatus | **156 tests passed, 78.455 seconds**, no skips or expected failures | Synthetic/fake-host apparatus and oracle calibration; zero model calls |
| Static checks | Ruff, JavaScript syntax, tracked-diff whitespace passed | Harness sources at the frozen validation checkpoint |
| Real TTT browser baseline | Base game passed 19 actions; guidance and recommendation checks detected absent features | Actual Chrome actions against the immutable pre-feature source |
| Composite verifier | TTT base behavior and GAS closure passed; source/input drift absent; review-owned checks remained unverified | Real browser adapter with strict response binding; no historical grade rewritten |
| GAS source closure | Retained TTT passed; retained Checkers failed unresolved relative `engine.js` | Source/runtime dependency path; no hosted execution |
| Real workspace identity control | Identical text produced distinct fresh run IDs; old state unchanged; explicit old-run recovery also preserved it | Seeded real-Git CLI fixture, separate from one-shot application runs |
| Returned TTT feature | Baseline base19 passed and guidance25 failed; returned candidate passed both; 26 product tests and GAS closure passed | Local Chrome and source review support incremental integration; the live benchmark is invalid |

Retained receipts:

- `result.json — final complete apparatus run: 156 passing tests` (external/private retained artifact; not included in this repository)
- `source-validation.json — 92-file source manifest and checks: frozen validation inputs` (external/private retained artifact; not included in this repository)
- `assessment.json — real browser replay: base pass and feature absence` (external/private retained artifact; not included in this repository)
- `ttt-base-game.json — strict composite driver replay: real baseline behavior` (external/private retained artifact; not included in this repository)
- `source-integrity.json — strict composite verification: no source/input drift` (external/private retained artifact; not included in this repository)
- `assessment.json — GAS closure calibration: opposite retained-product outcomes` (external/private retained artifact; not included in this repository)
- `assessment.json — identical-prompt workspace control: distinct identities` (external/private retained artifact; not included in this repository)

Two earlier broad test attempts ran while source writers were active and hit the
observer stability guard. They are development checks, not final validation.
Both complete runs after source freeze passed; the final one also includes the
strict response-schema fix. No model request was substituted with a fixture pass.

## Live evidence and limits

The prior full TTT and Checkers creates are documented in the
[baseline audit — product and workflow findings](shiploop-e2e-audit-2026-09-17.md).
They took 34m 28s and 42m 32s. TTT's catalog product checks passed, with workflow
evidence gaps; Checkers' local game worked but its GAS source closure failed.
Stricter replay leaves lifecycle attribution limits in both historical traces.

The full `ttt-guidance` attempt started in the existing TTT product as
CWD. It found the active workspace left by the earlier feature-prefix smoke and
successfully invoked `next` there instead of creating a fresh feature run. The
same prompt text does not make a new request an authorized recovery. This is a
retained isolation failure, not a valid fresh one-shot result; it remains
in the originally selected feature denominator. The control above establishes
that a fresh same-text workspace is supported by the script.

The native process finished with exit 0 after **79m 19s**, within its 80-minute
cap. The original result is **invalid-trial**: the selected ShipLoop package
changed during execution (10 files changed, two added). The observer stayed
stable. The separate recovery audit attributes 24 successful callbacks to the
old run and finds no fresh matching run. Neither condition is repaired by a
working product. The downstream best-move request was not launched because this
attempt is not an eligible clean predecessor. Original trial records and interim
qualifications remain unchanged.

The returned original repository is clean at `6fe8ad8`, with baseline `96f3ac3`
as an ancestor. Six existing files changed; no files were added or removed. Source
review confirms the original game engine, board handlers, and reset path were
extended with legal-move and active-player rendering. Actual Chrome checks found
the feature absent in the baseline and passing in the returned candidate while
base behavior remained passing. The pinned browser source exactly matches the
returned source. A separate rerun passed all 26 product tests and GAS closure.
This supports incremental **product** integration, not a valid benchmark run.

- `REPORT.md — completed feature audit: outcome, isolation, drift, and improvement experiments` (external/private retained artifact; not included in this repository)
- `returned-source-binding.json — source identity: browser evidence matches returned application` (external/private retained artifact; not included in this repository)
- `incremental-source-review.json — retained implementation: ancestry, integration, and 26 tests` (external/private retained artifact; not included in this repository)

This task did not edit production ShipLoop. Separate changes appeared in the
shared source tree during the live trial; the evidence does not identify their
actor. They were preserved. The 156-test result is a pinned apparatus checkpoint
before those changes, not validation of the subsequently changed ShipLoop package.

The retrospective inventory retains eleven launched attempts and six unexecuted
catalog steps (17 rows); it is not a preregistered A/B study. Its final report
preserves historical verdicts alongside comparison limitations:
`REPORT.md — retained attempts: complete accounting` (external/private retained artifact; not included in this repository).

Full implementation does not establish nine successful live runs. The supplied
bundled browser mapping supports the inspected TTT baseline only; an external
source-pinned mapping also verified this returned TTT feature. Other changed
output, Checkers, and Battleship still need reviewed mappings for their returned
UI. Missing adapters or reviews remain unverified. Hosted deployment,
authorization, consumer activation, replication, and production ShipLoop
improvement candidates remain separate experiments in the plan.

## Performance observation and limits

The independently captured 18:34 UTC snapshot contains 195 tool calls, including
97 reads, 27 text edits, 17 terminal calls, and six subagent dispatches. The run
was at `spec-improve`; the main product and its tests were unchanged. Five host
API error observations and two failed read updates are separate potential delay
sources. Repeated paths alone do not prove wasted work: stage transitions, new
reviewers, content changes, and cold recovery can justify rereading. Streaming
usage records must not be added into a token or billing claim.

`current-audit.md — bounded live transcript review: counts, source identity, and limits` (external/private retained artifact; not included in this repository)
retains the evidence and uncertainty. A performance pilot should first reconcile
unchanged repeated reads against those legitimate causes, then compare one
compact decision-locator guidance change if a supported gap remains. Preserve
the existing DAG, Improve review requirements, and product-quality gates.

The follow-up checked 17 exact request/returned-content clusters and 32 adjacent
read pairs. **Zero pairs were proven redundant**: each crossed a different
captured call-context identifier, while stage/reviewer/recovery attribution and
terminal side effects remained unavailable. This defers any repeat-read
optimization claim.
`repeat-read-attribution.json — contextual read comparison: no supported redundancy` (external/private retained artifact; not included in this repository).
Exact log prefixes and the archived state are retained under the audit's
`snapshot/` directory and checked against the original snapshot hashes.

The completed run's terminal event reports 194 model calls, 1,395,967 input
tokens, 202,417 output tokens, 31,106,816 cache-read tokens and USD 10.84915312.
These are host-reported terminal values, not an independently verified bill or
summed streaming chunks. Parent `xhigh` was requested; effective child effort
was not exposed. Skill drift and request reuse exclude a causal performance
comparison. Grok's final checks remained Node/source based, with hosted/browser
checks explicitly blocked. Our later assembled local Chrome replay supports a
pilot to distinguish feasible local interaction from deferred hosting; it does
not retroactively supply evidence Grok had when it completed the workflow.
