# Consumer-delivery pilot implementation and evidence

Scope: the reviewed [consumer-delivery plan](shiploop-consumer-delivery-plan-2026-09-15.md),
authorized by the subsequent request to implement. This work does not publish the
game, install an integration, change credentials, commit/push, or enable the pilot
by default. Baseline is `335a7b6` plus the pre-existing dirty worktree; unrelated
changes are preserved. The repository-context collector remains a separate plan.

During verification an external task advanced `main` from `335a7b6` to `7db930c`
with implementation-quality prompts, related guidance, and navigator tests.
Those changes remain intact. This task did not create those commits; final
checks use the combined worktree rather than assuming HEAD stayed fixed.

## Implementation

- `init --delivery-contract` opts a new navigator-v2 run into a typed declaration
  guard. Existing/unmarked runs retain their schema; old modes reject the flag.
- A pure helper derives the current contract/observations from accepted results
  in authoritative `state.md`. The script supplies contract/action bindings and
  stage-specific result templates; no new cursor, graph node, or Improve counter.
- Full contract corrections cannot be confused with partial observations.
  Required checks are gated by their current phase and candidate; authority
  references are declarations, not authentication.
- Effect, target/artifact identity, and consumer behavior remain distinct in
  packets and the HTML report. Partial successful effects survive recovery.
- Improved prompts challenge the original consumer outcome. Release planning
  finishes its non-executing plan and Improve campaign; release and consumer
  verification occur in their later existing actions.
- Portable card/README/reference guidance documents source-only, unresolved
  authority, scoped update, and late-replanning cases.

KISS limit: one activation target/operation, with multiple required consumer
checks. Distinct activation targets need direction; the guard does not invent a
deployment scheduler or reuse one target's authority for another. There is no
new package dependency, MCP integration, remote executor, or state store.

## Experiments and findings

The [experiment directory](../test/experiments/shiploop_delivery/README.md) retains
sanitized inputs, fixed oracles, frozen packet variants, and actual raw responses.
Each A/B response came from a separate `fork_turns=none` subagent with only one
packet and identical read-only instructions. Twenty-four observations cover six
sentinels twice for each variant. These are interpretation responses, not executed
ShipLoop actions or Improve reviews. Exact model-token and end-to-end timing
metrics were not collected; do not infer them from packet size.

The baseline already preserved most consumer/authority distinctions. Do not claim
the revised prose uniquely solved every sentinel. An exploratory timing defect
appeared in both versions: release-plan interpretations sometimes required later
synchronization and visual verification before completing planning. Original A/B
packets/responses are preserved. A separately labeled B2 clarification was tested
in four new fresh contexts: both approved-update cases assigned update/verification
to their later nodes; both missing-authority cases remained blocked on planning
facts. The phase-order metric was added after the original preregistration.

Two additional C recovery teachbacks used actual script-rendered packets and
accepted Markdown states. Both passed their separately graded orientation
checks: retain a successful declared update while consumer behavior is blocked,
and preserve a post-plan candidate-change block without replaying an effect.
These fixtures explicitly prohibit live operations; that limits conclusions
about how a host would act with real access. See the independent
[per-response assessment](../test/experiments/shiploop_delivery/assessment.md)
and [originating task labels](../test/experiments/shiploop_delivery/responses/provenance.md).

After adding explicit stale-precheck recovery wording, C's original candidate
packet was preserved and C2 captured the current rendering of the same state.
The separately graded fresh C2 response passed (1/1): remain blocked at release,
carry forward the stale precheck, obtain direction for a new planning run, and
do not perform or invent an update. This makes 31 retained interpretation
responses overall, not 31 executed workflows or independent model families.

The deterministic [guard controls](../test/experiments/shiploop_delivery/packets/C/guard-controls.md)
reject seven missing/contradictory transition declarations, admit their valid
counterparts, and demonstrate the difference with a test-only guard bypass.
An eighth source-only/optional-activation contradiction is rejected earlier at
schema validation; it is not mislabeled as a transition-bypass experiment.
The unmarked compatibility control still accepts the generic missing-evidence
result, showing what the opt-in guard adds without changing old runs.

Measured recovery packets are 9,748–10,073 UTF-8 bytes; the script-provided
delivery result field adds 367 bytes for one behavior observation or 591 for two
release observations in the measured formatted-JSON templates. These are sample
byte counts, not token costs, hard caps, or performance benchmarks. Full contract
authoring is heavier than an observation; normal stages do not repeat it. This
added authoring burden is another reason to retain opt-in status and evaluate
real use before default adoption.

### Actual local browser observations

The root tested the loopback-only HTML fixture with the in-app browser:

| Served case | Observed browser result | Meaning |
| --- | --- | --- |
| Working | Candidate 2; clicking Move piece displayed “Movement cue visible for the selected piece.” | A real fixture interaction produced the expected visible result. |
| Broken | Candidate 2; clicking Move piece displayed “Movement cue did not become visible.” | Matching candidate identity did not prove behavior. |
| Stale | The page displayed Candidate 1 while the local candidate fixture is Candidate 2. | Served and local identity are separate observations. |
| Login | Candidate 2 with “Login is required before movement can be evaluated.” and no move button. | No consumer interaction was established. |

These were four temporary loopback servers, not cloud deployments. The tab and
all four servers were closed/stopped after inspection. A worker independently
observed the working and broken cases too. Static HTTP and fake-boundary unit
checks are separately labeled; they do not replace these browser observations.

## Review and learning record

The latest seven full Git messages were read. Relevant lessons were to preserve
per-item ownership, current-candidate evidence, exact cold-recovery locators,
compatibility routes, and the distinction between completed checks and pending
release receipts. No history was treated as authority for an external update.

The first implementation review was material: it found `already-current` could
stand in for behavior, corrections could retain stale behavior evidence, and cold
packets needed stronger untrusted-data labeling and producer locators. These
findings prompted targeted repairs and regression checks. An apparent test-catalog
omission was rechecked and rejected as stale: the new suites were already listed.
No convergence is inferred from merely rerunning a test or receiving a callback.

Subsequent independent reviews found two more genuine bypasses: a resolved
local-only contract could omit consumer verification entirely, and an optional
activation declaration could coexist with no-activation scope and unresolved
authority. Regression tests now reject both. Every resolved contract requires a
consumer-behavior check, while a no-activation contract forbids effect/identity
rows even when optional. Earlier negative results can replace stale passing
observations at a later phase; release verification and terminal validation
retain those failures. A passed graph position cannot hide a newly reported
regression. Replanning instructions explain the fixed graph's recovery boundary.

Generated plugin parity was temporarily stale during these repairs; the plugin
view was regenerated from source, not independently patched. The report and
packet now include scoped approval locators and keep update effect, identity,
and behavior claims separate. This still does not authenticate any claim.

## Verification status

Final focused checks use the frozen guard source on `7db930c` plus the preserved
dirty worktree. The supported local toolchain is Homebrew Python/Ruff and the
bundled fallback Git, not Apple's license-gated wrappers. No tool was installed
and no license was accepted.

| Check | Observed result |
| --- | --- |
| Consumer-delivery guard | 19 tests passed, including rejected optional activation in source-only scope. |
| Public CLI opt-in/compatibility/relocation | 6 tests passed. |
| Navigator | 26 tests passed, including the concurrent implementation-quality additions. |
| Navigator dry run | 4 tests passed. |
| Delivery prompt fixtures | 6 tests passed. |
| Fake deployment boundary | 5 tests passed. |
| Browser fixture's loopback/static checks | 2 tests passed; registered in the existing ShipLoop group. |
| Installed-skill invocation | 7 tests passed after final package regeneration. |
| Test-group contract | 10 tests passed after fixture registration. |
| Scoped Ruff / Git whitespace | Passed. |
| Generated ShipLoop plugin parity | Passed after final regeneration. |
| C/C2 recovery and deterministic controls | Reproduction/integrity check passed; original C remains preserved. |
| Core hermetic group | 22 suites passed; `marketplace-run` failed for the environment reason below. |
| ShipLoop test coverage | All 70 current Python suites have passing results: 703 reported cases after final scoped reruns; the final Node async fixture passed separately. Aggregate-exit qualification below. |

The aggregate completed its original 69 Python suites (699 tests), including the
full managed and legacy action walks. The final 19-test guard rerun supersedes
its earlier 17-test result, and the newly registered two-test loopback fixture
passed separately. A catalog-to-log coverage check found all 70 current Python
suites, with no duplicate catalog entries or missing passing result.

**The ShipLoop aggregate itself did not exit green.** The root edited its shell
test list to register the loopback fixture while the runner was active. After
the first successful action walk, the still-running shell unexpectedly began
that walk again. The duplicate was interrupted; the aggregate therefore exited
1. The final async fixture then ran separately and passed. Shell syntax and
test-group checks pass for the frozen catalog, but those facts are not a clean
aggregate exit. Future full runs must use a frozen runner. No product test
failure was observed before that manual interruption.

The core failure is reproducible: `test/marketplace-run.test.sh` case M2 resets
PATH to its stubs plus `/usr/bin:/bin`, selecting Apple's Python and triggering
the unaccepted Xcode license. The non-wrapper toolchain passes the other core
suites. This unrelated test was not modified, and the core aggregate is **not**
reported green. The separate skill-authoring `quick_validate.py` could not run
because the selected Python lacks PyYAML; repository frontmatter/portability
checks passed instead. Neither limitation is hidden by an installation or skip.

The final independent candidate review found no remaining material issue after
the recorded repairs. The root re-read the latest seven full Git messages and
reviewed phase gating, correction/invalidation semantics, callback purity,
report escaping, opt-in compatibility, and documentation against that candidate.
These reviews are not described as a completed standalone Improve runtime or
as proof of a live deployment. No commit/push or application publication occurred
from this task. Logs are retained in the task and the local diagnostic directory
`/tmp/shiploop-consumer-verification.QGTtt8/`.
