# Agentic inner SDLC: implementation and experiments

```mermaid
flowchart LR
  P[Plan and acceptance examples] --> PI[Improve the plan internally]
  PI --> C[Implement bounded work]
  C --> T[Refine and author tests]
  T --> V[Verify and diagnose failures]
  V --> I[Improve the product internally]
  I --> G[Integrate and review affected changes]
  G --> O[Carry forward to system tests and outer Improve]
```

ShipLoop 0.9.2 strengthens six agent responsibilities in its existing stages.
The diagram groups the existing path for readability; the guide retains the
[full flat lifecycle diagram](../skills/shiploop/references/navigator.md).
Improve runs complete review/plan/apply/check/record/assessment cycles inside
one action until two consecutive trivial-only reviews have current checks and
no unresolved material findings. The agent then submits one completion; the
navigator records the result and selects the successor.

The [implementation plan](shiploop-inner-sdlc-implementation-plan-2026-09-14.md),
with an [eight-step native Backchain plan](shiploop-inner-sdlc-plan-2026-09-14.json).
It was written during implementation and is not a harness-validated schedule.

## Implemented responsibilities

| Duty | Existing stages | Practical change |
| --- | --- | --- |
| Challenge acceptance and test expectations | `step-plan`, `step-plan-improve`, `test-refine`, `test-author` | Use positive and nearby negative examples where ambiguity matters. Derive expected outcomes independently; for an important regression, reject the known-bad behavior when practical. |
| Own delegated integration | `step-plan`, `implement`, `integrate` | Define bounded ownership and shared interfaces. The owner inspects actual combined outputs and verifies the consumer path. |
| Diagnose persistent failures | `verify`, Improve campaigns | Record a testable diagnosis, a small observation that distinguishes causes, and the resulting next action. Change the approach when retries add no evidence. |
| Select relevant operational checks early | `step-plan`, `product-improve` | Assess changed authorization/data boundaries, dependency compatibility, recovery and diagnostics proportionately. Track each prerequisite at the stage that needs it. |
| Review the final candidate | Improve campaigns, `integrate` | Use available independent review on the final candidate. Material later changes invalidate affected review evidence and require reconsideration and current checks. |
| Retain or promote lessons deliberately | `document`, `skill-validate`, `carry-forward`, `outer-improve` | Keep local evidence, add a local regression, or propose shared guidance. Validate broader adoption against the trigger, a failure case and representative other tasks. |

The [guide responsibility table](../skills/shiploop/references/navigator.md#agentic-responsibilities-inside-existing-stages)
and [implementation constitution](../skills/shiploop/references/navigator.md#implementation-constitution)
make these duties explicit. Four canonical source files and their generated
package views changed. The graph tuples, runtime controller, saved state schema,
result envelope, shared Improve policy and policy pins remain unchanged.

Two additional prompt clarifications came from observed preview failures:
read **Current node and Action**, rather than the last accepted transition;
and distinguish prerequisites for current work from downstream release conditions.

For an actual input-to-result trace, the integration pilot supplied two locally
green components whose public adapter passed kilometres into a metre API.
`quote_cents(3)` returned 200 cents instead of the specified 425. At `integrate`,
the owner inspected the shared contract, inserted the existing conversion,
added a consumer test, reran checks and obtained independent review. One
accepted callback advanced the saved cursor to `carry-forward`. This works
because the owner verifies assembled behavior; the navigator does not detect
unit mismatches or certify the evidence. Unavailable release-only staging access
remains a release condition while otherwise-ready local work can proceed.

## Live pilots

The [preregistered criteria](../test/experiments/shiploop_inner_sdlc/preregistration.md)
were fixed before workers ran. Three fresh workers received only one public-CLI
packet and its isolated fixture. Earlier transitions were explicitly synthesized;
only the named current action was performed. Fixture specifications were
immutable, and the reserved oracle and reference implementations were withheld.
Root supplied an independent reviewer to the two pilots that needed one.

| Pilot / action | Seed reserved checks | Reference | Final worker | Saved unit tests | Accepted next stage |
| --- | --- | --- | --- | --- | --- |
| Misleading green / `product-improve` | 9/11 | 11/11 | 11/11 | 5 passed | `integrate` |
| Delegation interface conflict / `integrate` | 5/7 | 7/7 | 7/7 | 4 passed | `carry-forward` |
| Repeated failure / `verify` | 1/14 | 14/14 | 14/14 | 4 passed | `product-improve` |

All 32 reserved final checks passed; each spec stayed unchanged. Each worker
submitted one accepted callback and stopped at the requested boundary. The
[parent semantic assessment](../test/experiments/shiploop_inner_sdlc/evidence/live/semantic-grading.md)
found all five declared criteria satisfied for each final result. Full outputs,
source snapshots and actual candidate identities are in the
[live archive](../test/experiments/shiploop_inner_sdlc/evidence/live/README.md).

The allocation reviewer first found inadequate saved contract coverage despite
correct behavior and successful one-off probes. The worker had to add durable
regressions, reset its clean-review streak, and obtain another review before
converging. That finding remains part of the evidence rather than being erased
by the successful final result. Post-run evidence review also corrected an
ambiguous placement of the material edit in the next clean cycle's notes; the
original and explicitly amended records are both retained. The worker confirmed
a distinct no-edit review had followed the edit and commit before the callback.

The integration inputs were constructed contributor modules and reports. This
pilot tested owner integration judgment; it did not run two real contributors
concurrently. The diagnosis pilot tested a deliberately misleading cache/retry
note against a deterministic wrong-setting defect. It observed the different
results for `APP_PORT` and `PORT`, corrected key selection and explicit-`None`
validation, and reran positive and negative checks.

## Cold interpretation previews

These previews issued no callbacks and performed no implementation. Fixed case
criteria are in [cold-cases.json](../test/experiments/shiploop_inner_sdlc/cold-cases.json).

| Preview | Identity result | Semantic result |
| --- | --- | --- |
| Initial two cases | Wrong prior stage for risk case; action IDs not supplied | 10/10 case criteria; overall orientation defect preserved |
| Unblinded identity correction | Both literal identities correct | Diagnostic only, not a new pass |
| Fresh two-case repeat | Both literal identities correct | 9/10; wrongly blocked local work on release-only staging |
| Fresh risk-only preview after clarification | Correct identity | 5/5; staging is assigned to release |

The [cold evidence and grading](../test/experiments/shiploop_inner_sdlc/evidence/cold/grading.md)
preserve all five packets, original responses and the explicit correction.

Both the packet orientation wording and the requested response fields were
clarified before the fresh repeat. Therefore this is iterative capability
validation, not a controlled estimate of the wording's causal effect. The
single-case final preview demonstrates the intended stage distinction on that
scenario, not universal prerequisite reasoning.

## Method and validation

Before live execution, evaluator review found an incorrect reference treatment
of explicit `None`, insufficient boundary coverage, and possible cross-fixture
Python module caching. The references, reserved cases and loader isolation were
corrected, then fresh seed/reference calibration ran before workers were
launched. The live pilots use source commit
`44fcfbc1cfa77278187468c4cc194be103e2b5c0`; the final prerequisite clarification
was added afterward to `step-plan`, which none of those three live actions uses.
The final risk-only preview used that clarification. No reserved expected
outcomes changed after live execution began.

The original calibration's redundant `after` field means **reference**, not
worker result. That raw record is preserved and explained in the evidence.
The preparation script now uses only `before` and `reference`; a separate fresh
preparation reproduced all calibration totals after this reporting cleanup.

| Check | Result | Scope |
| --- | --- | --- |
| Navigator suite | 15 passed | Public CLI, state/callback behavior, prompt dispatch and persistence; repeated after the final prompt change. |
| Graph dry-run suite | 4 passed | Simulated routing and prompt inspection after the final prompt change. |
| Shared Improve policy suite | 5 passed | Shared policy compatibility on the production candidate; no policy change afterward. |
| Managed package relocation | 1 passed | Installed-package path portability. |
| Test-group suite | 10 passed | Existing suite inventory and routing. |
| Plugin generation and parity | Passed for all 18 packages/catalog entries | Full source-derived synchronization; only ShipLoop-related generated changes. |
| Policy synchronization, interop hygiene, Ruff and diff checks | Passed | Shared policy consistency, portable skill conventions, changed Python files and whitespace. |
| Fixture preparation | Passed | All seeded defects fail their oracle and all reference implementations pass. |

The full legacy delivery suite was not rerun for these prompt/documentation
changes. The focused tests establish protocol/package compatibility; the
behavioral pilots assess the new responsibilities separately. File existence,
a callback receipt, or a model's completion claim alone did not count as a
successful behavioral check.

## Decision and limits

Adopt the narrow prompt/constitution changes and keep these opt-in fixtures for
regression work. Preserve agent-owned Improve and the simple navigator. No new
mandatory nodes, result fields, byte-comparison gates, installed integrations,
or automatic global-skill promotion were introduced.

The earlier recommendation drew on primary accounts of
[harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps)
and [agent evaluations](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).
Those sources motivate independent evaluation and explicit outcomes but also
show that harness complexity has costs. Local evidence supports the bounded
change; it does not show that more stages or controllers would help.

These are three small, instructed capability pilots plus interpretation
previews. They do not establish an accuracy rate, an A/B improvement over the
previous prompts, cross-model/host behavior, or real release safety. A larger
matched trial with equal review budgets and genuine concurrent contributors
remains an optional next experiment. No installation or deployment trial was
part of this delivery.

## Final review

An independent reviewer inspected the complete source and staged evidence
candidate against `a813561` and found no actionable correctness, portability
or evidence issue. It confirmed unchanged navigation/runtime boundaries,
synchronized generated views, and accurate disclosure of synthetic scope,
initial failures and the post-run note clarification. Its independent navigator
and dry-run reruns passed 15 and 4 tests, and staged/unstaged whitespace checks
passed. The parent also checked archive reconstruction (all 13 saved unit tests),
JSON parsing, report/plan links, and the actual source diff.

The reviewed work is isolated on `codex/shiploop-inner-sdlc`. The final report
records candidate validation; actual merge and push results are verified during
delivery and reported separately. Unrelated main-worktree research and test work
is outside this change. No new executable or prompt change followed this review.
