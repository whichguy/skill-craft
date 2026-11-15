# R08 implementation evidence

**R08 is implemented at `d6721a5020bfd36c912ac59256a1672a61d4d86c`.** Nine affected full suites passed 1,811 tests. Follow-up checks passed another 121 test executions, including 22 after the latest release integration. Release-boundary, production lint and the no-added-findings lint comparison passed. An independent Astra/high review approved the runtime change. [Acceptance receipt](acceptance.json), [source identity](source-identity.json), [review](review/final-review.md).

The runtime uses one current receipt format, `shiploop-test-loop/v2`. There is no separate judgment-version field or receipt migration. R08 adds no prompt wording: the existing scripts enforce the rule for every software package.

| Situation | Before | After |
|---|---|---|
| Exit zero with `1 passed, 1 error` | Accepted with `ran=1, failed=0` | Refused with `ran=1, failed=1` |
| Same-input pass saved under missing/v1 schema | Could bypass current judgment | Commands rerun; current results decide |
| Whole-answer yes from earlier semantics | Package version alone did not isolate same-version changes | Its key binds the same `test_schema` constant |
| Current v2 receipt with matching inputs | Reuse available | Reuse remains available with provenance |

Errors are added to `failed` after calculating `ran`; setup/collection errors cannot certify additional executed tests. Existing no-tests, minimum-count and missing-ID precedence remain. [Count reader](../../../skills/shiploop/scripts/shiploop_test_counts.py#L55), [candidate judge](../../../skills/shiploop/scripts/shiploop_test_loop.py#L836), [base judge](../../../skills/shiploop/scripts/shiploop_test_loop.py#L1903).

## Acceptance at the actual reuse paths

| Required behavior | Executable evidence |
|---|---|
| Mixed errors refuse focused, regression and check judging; base behavior and clean-pass controls remain | [Judge regression](../../../test/shiploop-test-counts.test.py#L233) |
| Missing/v1 candidate receipt reruns on the same tree and leaves acceptance state unchanged | [Candidate callback](../../../test/shiploop-test-loop.test.py#L2778) |
| Earlier whole-answer yes cannot bypass rerunning; every other key field stays equal | [Whole-answer callback](../../../test/shiploop-test-loop.test.py#L2815) |
| Actual step-Proof callback refuses mixed errors | [Proof callback](../../../test/shiploop-test-loop.test.py#L3070) |
| Missing/v1 check and numbered Proof receipts rerun | [Both Proof receipt paths](../../../test/shiploop-test-loop.test.py#L3083) |
| Current v2 candidate and Proof receipts still reuse | [Candidate control](../../../test/shiploop-test-loop.test.py#L2805), [Proof controls](../../../test/shiploop-test-loop.test.py#L3119) |
| New main TAP behavior also applies after upgrade: nine actual points fail minimum 40 | [TAP upgrade regression](../../../test/shiploop-test-loop.test.py#L4068) |
| Analysis reads a record actually emitted by the v2 producer | [Producer-to-reader regression](../../../test/shiploop-e2e-fidelity.test.py#L854) |

The Proof positive control proves reuse and then stops at a later gate; it does not claim full advancement. Existing whole-answer completion controls cover successful advancement. Runtime reuse requires v2. The report reader still measures frozen v1 archives and current v2 records; that historical reporting cannot authorize execution reuse. [Reporting reader](../../../test/shiploop_e2e/fidelity.py#L500).

## Completed verification

| Full suite | Tests | Source | Result |
|---|---:|---|---|
| shiploop-test-counts.test.py | 71 | `7add5485` | PASS |
| shiploop-test-loop.test.py | 211 | `7add5485` | PASS |
| shiploop-handoff.test.py | 170 | `7add5485` | PASS |
| shiploop-domain-words.test.py | 5 | `7add5485` | PASS |
| shiploop-e2e-fidelity.test.py | 149 | `5a3c91dc` | PASS |
| shiploop-e2e-analysis.test.py | 299 | `5a3c91dc` | PASS |
| shiploop-e2e-delta.test.py | 90 | `5a3c91dc` | PASS |
| shiploop-run-review.test.py | 688 | `5a3c91dc` | PASS |
| shiploop-e2e-hosts.test.py | 128 | `5a3c91dc` | PASS |

Release-boundary, production-runtime Ruff and the baseline lint comparison passed, along with the 17 additional selected core methods and 10 final-integration Grok hook fixture controls. Each verification bank retained its HEAD, clean status and complete tracked `skills/` and `test/` inventory throughout execution. No failed test was retried on unchanged source. Exact commands, output, timings and exits are in the [earlier receipt](verification/earlier/receipt.json), [current receipt](verification/current/receipt.json), [integration receipt](verification/integration/receipt.json), [test repair](lint-repair/handoff.json), [final lint receipt](verification/lint/receipt.json) and [final release integration](verification/release/receipt.json); [acceptance.json](acceptance.json) selects each full suite once.

Main advanced with host-harness changes while the core bank was running. The four core suites ran at `7add548509256e78c8b571ef852d209959b60a24`. The entire ShipLoop runtime scripts tree, nine of the 11 R08 files and the unchanged core support files are byte-identical at `d6721a5020bfd36c912ac59256a1672a61d4d86c`; the [identity receipt](source-identity.json) records those comparisons. Five affected harness/consumer suites and the 17 focused core methods ran at `5a3c91dce4ddf20916d71c135bdd00c174fe6a3f`. The final integration is based on main `59d8dc3ed4eb70bc096a95e54e4e1ce49da0e4e3`. The last release adds house-style record guidance and advances the package version, which is an answer-key input; the final 22-method focused bank therefore reruns the R08/TAP paths and generic-text check on that version. None of the 10 R08 Python files changed. Earlier CI, distribution and retained-probe updates leave the runtime scripts unchanged. The only new retained fixture consumed here is the Grok probe archive; all ten existing hook controls were run again after that integration, before the two test-only repairs. Earlier reporting passes are retained but not counted twice. The independent diff review inspected `7add548509256e78c8b571ef852d209959b60a24`; its production R08 diff is unchanged; the later five-line fixture cleanup below received parent diff review and affected-test reruns. Large raw inventories and transcripts remain referenced in [external-evidence.json](external-evidence.json).

The original ten-file Ruff command failed with 987 findings. A base comparison identified 984 existing findings plus three new test-fixture warnings: one shadowed variable and two loop captures. The two affected tests were repaired without changing assertions or production behavior, then 72 test executions passed with the exact two-file patch and all 12,403 tracked hashes stable. The repair receipt records that intentional dirty state; it is not labeled a clean checkout. The final ten-file comparison found 984 current and 984 baseline findings, with zero additions or removals; production runtime files pass directly. Both earlier lint failures remain in the retained receipts. Raw diagnostic outputs too large to duplicate here remain hashed in the external manifest. No unrelated lint repairs or suppressions were added.

The final review requested `gpt-6-astra` with `high` effort through a fresh `shiploop-judge` session. Implementation used fresh `gpt-6.1-sol`/`medium` sessions; routine validation used the matching fresh native test-runner role. Launch controls establish the requested routing, not independently verified server-served identity. [Review launch](review/final-review-launch.json), [roll-forward launch](roll-forward/worker-launch.json), [integration launch](post-rebase/worker-launch.json).

## Earlier attempts retain their actual status

The original corrected pre-fix runs produced **20 assertion failures and zero fixture errors** across seven selected methods. These are assertion failures, not 20 tests. The earlier fixture-reset error is retained separately. The first candidate's nine green methods are historical evidence; they included a floor-compatibility control later removed at the owner's simplification. [Original outcomes](worker/outcomes.json).

The owner then authorized a simple roll-forward format. The 28-suite quick bank for the superseded candidate was stopped after four completed passes, with no observed failure; its final status is **INCOMPLETE/superseded**, not PASS. Its inner runner receipt remains partial. [Cancellation receipt](superseded/receipt.json).

The schema-only worker passed 18 selected methods with stable green source hashes. Its red attempt has an incomplete overall identity because an unselected historical fixture was restored during execution; it is not claimed as a fully stable red run. After rebasing onto main's TAP release, all 17 selected integration methods passed with stable source. The nine unique full suites above, with their explicit source identities and invariance checks, are the final acceptance evidence. [Roll-forward handoff](roll-forward/handoff.json), [post-rebase handoff](post-rebase/handoff.json).

## Boundaries and remaining work

The [plan](../../shiploop-implement-step-fix-plan-2026-10-17.md#r08--truthful-verdicts-and-receipt-reuse) marks the requested R08 scope implemented and retains the other recommendations. The [source map](source-map.json) refreshes all 22 recommendations, eight considerations and fourteen craft rules, including the changed R08 consumers and tests. The [document check](validate_sources.py) verifies pinned bytes, excerpts, IDs, links and retained results; it does not replace behavioral tests. Markdown visual rendering was not inspected.

R21's mutable external target/fixture/authority freshness remains separate. No live platform delivery, prompt-quality comparison, historical-run migration, retry-aggregation redesign, installed-host qualification, publication or release is claimed. Future judgment changes that invalidate saved passes bump the existing receipt schema.
