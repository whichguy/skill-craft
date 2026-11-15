# R21 implementation evidence

**R21 is implemented. Four full suites passed 484 tests, including 11 new regressions, and the final independent review approved the change.** The tested and reviewed source is `4087731ff6ce672d635df7e479b890c2c2d66d96`; the integrated source is `cc9df6d2c9413a586147392f10149f138905e935`. [Acceptance record](acceptance.json), [final review](final-review.md), [integration identity](integration.json).

One shared eligibility predicate now prevents a passing receipt from replacing a fresh observation at a declared external boundary. The runtime retains `shiploop-test-loop/v2`; no new field, migration, cache layer or Until Loop directive is introduced.

| Reuse path | Change | Behavioral evidence |
|---|---|---|
| Whole check answer | Eligibility precedes `matching_yes` and `take_check`; release verification always evaluates again. | Actual system-test and release completion refuse after the sibling fixture changes, including the returned-result copy. |
| Candidate receipt | Targeted, host-dependent and recognized remote commands execute again; actual overrides use the same predicate. | System-test refuses with its whole-answer receipt removed; explicit host-dependent overrides also rerun. |
| Step Proof | Both check and numbered receipts require eligibility. Declared strategy targets or unsafe item commands also veto reuse. | Targetless Proofs rerun in an external strategy; old numbered evidence remains unchanged. |
| Mutation observations | Eligibility checks the full focused set before remote rows are filtered. | Host/target metadata changes and mixed remote rows rerun the actual tests against changed external state. |

The policy lives in [reuse_eligible](../../../skills/shiploop/scripts/shiploop_test_loop.py#L1370); its consumers are [_reused](../../../skills/shiploop/scripts/shiploop_test_loop.py#L1410), [step_proof](../../../skills/shiploop/scripts/shiploop_test_loop.py#L1662), [_reusable](../../../skills/shiploop/scripts/shiploop_mutation.py#L429) and [dispatch](../../../skills/shiploop/scripts/shiploop_navigator.py#L10324). The [allowed/denied/allowed regression](../../../test/shiploop-test-loop.test.py#L2851) separately observes a permission denial, then accepts a fresh passing result while preserving the failed receipt. Existing local candidate, whole-answer, Proof and disposition-only mutation controls still reuse receipts with provenance and count floors.

`keeps_state=no` does not establish locality: a stateless service can change its answer. Checkout commands already omit `target`. This conservative rule can add a run for an unnecessarily named checkout target or a local Proof in a mixed strategy. It makes no performance claim. [Decision and advice disposition](decision.md), [design review](design-review.md).

## Exact validation

All commands below ran in the clean, isolated source worktree at `4087731ff6ce672d635df7e479b890c2c2d66d96`, with `SHIPLOOP_PROGRESS=off`. The full argv, environment override, timestamps, exits and raw output paths are in [acceptance.json](acceptance.json). No test was retried and no test was skipped.

| Suite | Tests | Result |
|---|---:|---|
| `python3 -B test/shiploop-test-loop.test.py` | 222 | PASS |
| `python3 -B test/shiploop-callback-contract.test.py` | 102 | PASS |
| `python3 -B test/shiploop-navigator-contract.test.py` | 149 | PASS |
| `python3 -B test/shiploop-package-integrity.test.py` | 11 | PASS |

The release-boundary check and `git diff --check` also passed. The final reference is 8,191 bytes against the unchanged 8,192-byte limit. Ruff found no added diagnostics: six navigator warnings and one test-file warning were already present; the other three runtime files are clean. This is a [baseline comparison](lint-comparison.json), not a claim that the raw whole-file lint command exits zero.

The collector reported **INCOMPLETE for its generated-output audit**, despite all six commands passing: 43 ignored Python bytecode files appeared outside the declared output paths. HEAD and all 12,636 tracked-file hashes stayed unchanged. The parent verified each cache's interpreter header and corresponding current source timestamp/hash and size, removed only those files from this session's verification worktree, and rechecked every tracked hash and clean status. The [original receipt](validation/receipt.json) remains unchanged; the [separate artifact resolution](validation/artifact-resolution.json) records cleanup. No test rerun or source repair was needed for that artifact deviation.

## Failures retained and review repairs

The [regression receipts](regressions.json) retain every initial and corrected attempt with raw output and source identity. The first baseline run includes a missing new predicate and two mutation-fixture setup failures; those are not freshness proof. The corrected baseline restores valid mutation fixtures and demonstrates the actual-override and returned-result failures. Earlier valid cases demonstrate system-test, in-place release, denied access and both Proof caches. Both baseline runtime snapshots match pre-R21 main.

The [first independent review](initial-review.md) requested three repairs: an uninitialized variable on accepted/inactive check replay, an oversized reference, and a mutation refusal still promising reuse unconditionally. The replay regressions reproduced the error before repair. Accepted checks now acknowledge prior acceptance without gates; inactive unaccepted checks refuse with existing recovery/resume commands. The reference was condensed and mutation guidance now qualifies reuse. The [final review](final-review.md) approved the exact source and independently verified the three repairs. [Launch controls and source hashes](reviews.json) record requested Astra/high routing; they do not independently attest a provider-served model identity.

## Plan, integration and limits

The [plan](../../shiploop-implement-step-fix-plan-2026-10-17.md#r21--freshness-at-external-boundaries) marks R21 implemented, shows literal before/after callback wording and keeps R07/R05 next. All 22 recommendations, eight considerations, fourteen Code craft rules and T1–T52 remain accounted for in the [source map](source-map.json). The [changed-excerpt record](anchor-changes.json) preserves prior claims as comparison data; current claims are in the source map. The [document check](document-check.json) verifies 186 anchors across 41 source files and the retained test receipts. Rerun it from the repository root with `python3 -B docs/shiploop-implement-prompt-audit-evidence/r21-20261115/validate_evidence.py .`.

Published main `7fb5ba64f019230c24b5f3099d4154357dc6891f` added E17 study apparatus, the oracle port retry and E2E improver defaults during this task. Integration preserved all seven R21 files, the full `skills`, `scripts` and test-fixture trees, and the four selected suites plus their support files byte for byte. The host-code anchor's file hash was refreshed; the cited method did not change. The earlier tests and review retain their actual source revision. Separate sessions published their experiment/harness work; this task did not modify their stashes or trials.

Targetless rows retain the existing checkout contract; arbitrary undeclared environment or shell dependencies are not detected. The live permission-result fixture is not an authority-expiration engine. Document/Improve scheduling and remote mutation execution/scoring remain unchanged. No live platform, installed-host, deployment, full-repository, CI, publication or prompt-quality comparison is claimed. Large raw inventories and transcripts remain hashed in the [external evidence manifest](external-evidence.json). Markdown visual rendering was not inspected; links, fences and source spans are checked structurally.
