# ShipLoop prompt navigator implementation

Base: `12a488d2e8d753f285c538fae1f1b6d95fba7941`. Status: implemented and
verified. This implements the pending simplification discussed
after the managed Improve rollout and graph harness. It supersedes that
rollout's ownership model for new runs; existing run records remain compatible.

## Decision and boundary

Make a small prompt navigator the default for new runs. Keep the established
SDLC responsibilities visible and make each Improve campaign one action.
The host performs the work and judges its meaning; the script records declared
results and follows the graph. No new external runtime or integration is added.

Retain action identity, structurally valid transitions, idempotent replay,
locking, safe paths, and crash-recoverable Markdown writes. Remove product,
requirements, policy, controller, evidence and certificate byte checks from the
new execution path. No test execution, Git command, semantic classifier or
Improve pass counter belongs in that path. A declared completion must be
presented honestly, without implying independently verified delivery.

## Graph and execution

The [navigator guide](../skills/shiploop/references/navigator.md) defines the
flat graph and its whole-action Improve binding. Prelude: intake, repository
and environment discovery, research/Improve, specification/Improve, early test
strategy, and dependency-aware plan/Improve. Each ordered work item has local
plan/Improve, implementation, test refinement, executable tests, documentation,
optional skill validation, checks, product Improve, integration and carry-forward.
Outer actions cover system tests, whole-product Improve, release planning,
authorized release, consumer verification and handoff.

The host orders work by real dependencies. The script consumes that ordered
queue; it does not invent another dynamic task-DAG planner. Plan/plan-improve
can replace pending work before execution. Carry-forward can replace future
work while preserving completed/current work. Improve internally repeats
review/plan/apply/check/record/assess until two distinct consecutive trivial-only
reviews; the script receives one completion after the host's assessment.

## Implementation slices

1. New pure navigator state/transition module plus small persistence/packet
   adapter using existing lock and transaction storage.
2. Independent prompt catalog and owner binding; preserve test planning,
   code-informed test refinement, skills, broader obligations and constitution.
3. Early marker dispatch and new-run default in the existing CLI. Old managed
   and legacy runs retain their own validators and renderer. No conversion.
4. Default graph dry-run uses the same navigator and full packet renderer.
   Preserve the previous command as `managed-graph-dry-run` for compatibility.
5. Tests cover the new default and preserve older protocols through explicit
   fixture modes. Regenerate package views from source.

## Acceptance and checks

- Complete a two-work-item real CLI walk from an empty non-Git directory with
  only declared results; no product edits, Git or test commands from navigator.
- Exercise every normal node, optional skill branch, repeat, block/resume,
  pause/resume, halt and future work changes with expected graph edges authored
  independently of the route table.
- Reject stale action IDs, conflicting replays, malformed mode markers,
  arbitrary successor fields and unsafe state/result paths without advance.
- Prove interrupted transaction recovery and preserve literal requests and
  reasons, including shell-sensitive text, CRLF and Unicode.
- Allow product/evidence/policy content to evolve without quality gates; test
  that forbidden old validators and command executors are never called.
- Verify cold packets name the actual task, scope, notes, policy and callback.
  Improve instruction occurs once and lets the host own its complete loop.
- Run the affected protocol/packet/storage/transport/graph suites and the two
  established complete delivery walks as compatibility checks. Check package
  relocation/parity, meaningful lint, and the independent final review.

## Verification and release

- All 63 suites enumerated by `test/shiploop.test.sh` passed in the initial
  623-test regression run. The
  first 53 suites ran serially; the remaining ten isolated suites ran in two
  parallel processes. The sequential wrapper was retired at the planning-suite
  boundary to avoid duplicate execution. Both managed and legacy complete
  delivery walks passed.
- The final navigator suite passed 12 tests after the inbox-creation fix and
  addition of a public-CLI regression, bringing the validated suite inventory
  to 624 tests. That CLI test completes two work items across 36 transitions,
  cold-recovers at every stage, and follows the actual packet's canonical
  result paths and completion commands. Four dry-run harness tests also pass.
- The public dry run passed eight independently expected scenarios and 202
  transitions. A relocated generated package worked from a path containing
  spaces against an empty non-Git directory.
- Source/generated-package parity, skill interop hygiene, test-group coverage,
  meaningful Ruff checks and `git diff --check` passed.
- Independent reviews found and resolved callback input/receipt collisions,
  missing prior-result context in cold packets, and missing atomic inbox
  creation. Two final independent reviews reported no actionable findings.
- An explicit Improve-node `repeat` remains an attempt restart, never a clean
  review or convergence credit. Normal Improve reviews stay inside one action.

Upstream `2692be8` changes CI, Review Coverage, catalogs and documentation;
its changed paths do not overlap this candidate. Integration retained identical
ShipLoop production files. The final navigator suite (12 tests), dry-run suite
(four), updated test-group checks (ten), Review Coverage checks (133), and
full generated-package parity check passed on the integrated baseline. The
added public-CLI test also received an independent review with no findings.

No simulation is evidence of application behavior or deployment. Git delivery
of this skill change does not claim an application deployment or a live-model
evaluation of every prompt.
