# ShipLoop local-skill integration plan

Status: implemented and verified, 2026-09-18.

## Outcome and evidence

Make repository-local skill reuse available before implementation, and make its
selection recoverable by Improve and later items from durable repository files.
Keep the existing late assessment for learnings discovered during the work.
The [completed capability trials](shiploop-local-skills-2026-09-18.md) support
unchanged reuse, compatible evolution, a separate skill, and no skill work.
They do not prove autonomous selection across a full delivery run.

Ready: the current v3 graph, generic result envelope, work-item context, repository
knowledge index, and selected Improve runtime already provide the needed routes.
No new state fields, scheduler, dependency, host install or global skill mutation
is required. Preserve all unrelated work already present in this checkout.

## Changes

1. Route the focused local-skill guide into `discovery` and `step-plan`, as well as
   the existing `skill-assess` and `skill-validate` checkpoints. Before planning,
   inspect the existing index and relevant skill contracts. Record fit or no fit;
   retain selected entrypoints, effective inputs/default sources, product contract
   and revalidation conditions in existing plan/evidence notes. Put a compact
   locator in each relevant work item's context when the plan creates it.
2. Make the conditional Improve handoff explicit: retain relevant selected-skill
   locators in the child contract/review notes, review fit/defaults/compatibility,
   and distinguish host-authored semantic evidence from runtime receipt checks.
   The host still authors the child contract; the parent packet cannot do that.
3. Maintain one repository index route during carry-forward so newly created or
   evolved skills are discoverable by the next item/run. Preserve old supported
   uses. Keep changing task data in evidence and stable procedures in local skills.
4. Clarify the shared guide's v3 result encoding and isolate legacy receipt rules.
   Do not change either protocol's schema or traversal.
5. Add regressions to the existing CI suites for early/late cold routing, selected
   local-skill handoff through the actual Improve CLI, and legacy-field rejection.
   Keep synthetic navigation and host-authored decisions explicitly labeled.
   Synchronize the generated ShipLoop plugin view using the existing generator.
6. Repair the preexisting README link that the baseline relocation check found:
   identify the source-only E2E README by its checkout-relative path, preserving
   the existing instructions without a broken link in installed packages.

## Verification and done criteria

- New early-routing regression fails on the pre-change prompt catalog.
- Cold producer and pending Improve packets retain local-guide/index locators;
  selected skill evidence survives the real child runtime's cold callback path.
- A later item can reopen the maintained repository index; previous item context
  is not silently presented as the next item's selection.
- V3 rejects legacy receipt fields; legacy documentation checks continue to pass.
- Focused guidance, navigator, actual Improve CLI, reference-routing,
  iteration-documentation and packet-bound suites pass. Package parity passes.
- Independent review of this turn's scoped delta has no unresolved material issue.
- Report exact checks and remaining limits. Do not claim semantic full-run proof,
  automatic host discovery, token savings, publication or global installation.

## Execution record

Implemented the six changes above. Source changes are in the v3 prompt catalog,
testing/documentation and project-knowledge references, and the ShipLoop README;
the generated ShipLoop plugin view was synchronized with the existing script.
The runtime graph, result schema and storage code are unchanged by this work.

The new cold-route test failed at `discovery` and `step-plan` before the catalog
change, then passed. Baseline checks also found an existing README Markdown link
that escaped the installed package. Replacing it with an explicit source-checkout
locator preserved the audit instructions and restored the relocation check.

| Check | Result |
| --- | --- |
| `python3 -B test/shiploop-v3-guidance.test.py` | 10 passed |
| `python3 -B test/shiploop-navigator-v3.test.py` | 22 passed |
| `python3 -B test/shiploop-actual-improve-cli.test.py` | 7 passed |
| `python3 -B test/shiploop-reference-routing.test.py` | 8 passed |
| `python3 -B test/shiploop-iteration-docs.test.py` | 7 passed |
| `python3 -B test/shiploop-packet-bounds.test.py` | 7 passed |
| `python3 -B test/experiments/shiploop_local_skills/test_packet_routes.py` | 1 passed |
| `bash scripts/sync-plugin-views.sh --check shiploop` | Passed |

Total: 62 focused tests passed. The three extended production suites are already
in the ordinary `test/shiploop.test.sh` inventory; no new suite registration was
needed. The experimental cold-route check remains opt-in.

The actual CLI case submits a `skill-assess` result, binds the selected Improve
card, starts the real ephemeral child, retrieves its packet through a separate
cold callback process, completes it, and imports the receipt back to
`skill-validate`. It verifies the index/card/default-contract/validation resource
locators survive. The host-authored child context, preceding navigator transitions
and review judgments are fixture data. This proves runtime composition and resource
durability, not autonomous selection, semantic skill execution, or a full delivery.
The two-item regression keeps the shared repository index locator available while
excluding the previous item's selection from the next item's context. It does not
simulate a model learning or selecting a new skill.

Independent review found one conflicting discovery instruction: a blanket
read-only rule could suppress normal knowledge-index maintenance. It was narrowed
to skill-package edits; the reviewer verified the fix and reported no remaining
material issue in production or test changes.

The pre-change files for this implementation turn are preserved outside the repo
at `/Users/dadleet/tmp/shiploop-local-skill-integration-20260918`. Existing unrelated
edits were retained. No commit, push, publication, dependency or global installation
was performed. Full repository CI, a full autonomous ShipLoop run, host `/clear`
and token savings were not tested.

## Follow-up: ongoing regression coverage

The follow-up review found no additional ShipLoop runtime change warranted. It
identified one missing prompt-output guard: the actual-child fixture supplied
resources manually, so resource durability alone would not detect removal of the
host's handoff instructions. The existing real CLI test now checks those duties in
the bound, cold-recovered parent packet before authoring the fixture child context.
Removing that paragraph in a disposable package produced the expected test failure;
the unchanged production package passed.

Added `test/shiploop-local-skills.test.py` to the ordinary ShipLoop inventory
(now 84 suites). Its eight tests replay all ten historical observations from
relocated temporary copies, preserve the original incident ambiguity, exercise
negative grader controls, and check that preparation retains local skill bytes
while stripping previous task outputs. The evidence archive remains unchanged.
The suite checks the apparatus, not new model behavior.

Those controls found a grader bug: Python object equality accepted numeric `0`
for JSON `false`, and `true` for an integer attempt of `1`. Both regressions failed
before the fix. The grader now compares canonical JSON for main and compatibility
outputs, preserving scalar types while ignoring object key order. All ten archived
grades are unchanged after this fix.

Follow-up verification: 8 local-skill apparatus tests, 7 actual-Improve CLI tests,
and 14 inventory/sharding tests passed (29 total). Scoped package parity and
whitespace checks passed. Independent review found no remaining material issue.
No production prompt/runtime changes were added in this follow-up.

Fresh model trials remain explicit: repeat the relevant create/reuse/evolve/split
cases when changing their behavioral guidance or evaluating a different host/model.
Neither fixture replay nor a synthetic child review establishes autonomous skill
selection, host `/clear`, or end-to-end delivery quality.

## Release integration

Prepared the task-only delta in an isolated checkout of published `origin/main`
at `7f8ef5d`, preserving the newer state/data, Backchain and context-reset changes.
The shared checkout's divergent history and unrelated working edits were not
included. The published base already has the required ephemeral Improve runtime;
this task changes no runtime implementation. Its CI inventory now has 88 suites,
including the new local-skill apparatus suite.

The source-only E2E README section that needed a link correction in the shared
checkout is absent from this published base; that unrelated section was not
copied into the release. Historical experiment artifacts remain byte-preserved,
including literal diff-context whitespace in `guidance.patch` and the extra final
newline in `final-checks.json`; source and test whitespace checks pass separately.

Release verification on the merged composition through upstream `88e59f9`:
82 focused tests passed across v3 guidance (15), navigator (22), actual Improve
CLI (7), reference routing (8), local-skill apparatus (8), suite inventory (15),
and packet bounds (7). Full generated-package parity passed for all 18 skills.
The merge preserves upstream test-facility handoffs, CI trigger policy, and
Backchain's direct Until Loop convergence contract. Independent compatibility
review found no remaining publication blocker.

A separate full `bash test/run-all.sh` aggregate was launched against committed
feature `5aafc54` on base `7f8ef5d`; it is not included in the focused count above
or claimed as validation of the later upstream composition. Normal main-branch
CI checks the exact published merge. The original shared checkout and its empty
staging area were left in place; publication used isolated worktrees.
