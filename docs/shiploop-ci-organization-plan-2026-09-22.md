# ShipLoop test organization and CI delivery plan

The accepted audit calls for latest stable toolchains, explicit smoke/component/full boundaries, complete deterministic qualification, and less fixture coupling. Existing user-facing test commands will remain available. This work changes test infrastructure and documentation; supported runtime behavior and historical compatibility assertions remain covered.

Baseline: skill-craft `8744d8fed103fa5eebe8b8ce49912d41fbb634ec`, matching fetched `origin/main`. Work occurs on `codex/shiploop-ci-organization` in an isolated worktree. The prior audit's two documents will be preserved as historical evidence, clearly linked to the implemented policy.

## Dependencies and acceptance

| Step | Depends on | Concrete result and verification |
|---|---|---|
| Baseline | Current source identity | Real smoke and package-parity results for the unmodified baseline; failures retained as prerequisites |
| Shared inventory | Baseline | One explicit hermetic catalog drives full, smoke, component unions, listing and balanced ShipLoop shards; unknown selections fail before execution; no duplicate suite execution |
| Complete qualification | Shared inventory | Source E2E apparatus joins full, historical Ask-Agent experiment receives an explicit full-only home, named Ask-Agent and composition selections include dependent adapters |
| CI policy and receipts | Shared inventory | Latest stable Python/Node and GitHub runner images; main/code PRs full, docs-only PRs smoke, manual choice; exact checkout identity, selected/completed results and retained logs; failed/cancelled/missing jobs cannot pass the aggregate |
| Fixture organization | Baseline | Shared setup/helpers live in non-test support modules; imports no longer require instantiating unrelated test classes; isolated repositories and process cleanup preserved; pure convergence predicate uses valid receipts in a cheap suite |
| Current dependency compatibility | Baseline | Explicit selected Dispatcher package is exercised through offline composition; latest published upstream SHA and package identity recorded; missing inputs fail, no native/model claim |
| Documentation | Prior steps | One concise command/policy table plus fixture ownership and evidence boundaries; audited historical counts are not presented as the new inventory |
| Delivery | Independent review and focused checks | Commit and push candidate, run complete PR CI on its merge candidate, merge without force after success, verify pushed main and full main CI |

The source E2E apparatus is a declared no-model catalog entry. Its named diagnostic groups overlap, so full qualification invokes its `all` selection once. Copied-package mock checks remain because they test relocation and package binding.

The runner will use Python's standard library and existing shell entrypoints, with no new test framework or installed dependency. Component selections form a union in catalog order. ShipLoop shards partition that inventory and use checked-in timing estimates from the audit; unknown durations receive a deterministic default. Receipts are opt-in and must go outside the checkout. They record source identity, runtime versions, selected suite IDs, outcomes, elapsed time and logs, never credentials or arbitrary environment dumps. A failed suite does not suppress the remaining selected checks or final receipt.

PR routing uses an explicit docs-only allowlist and merge-base-aware changed paths. Source skills, generated plugin payloads, tests, scripts, workflow changes, deletions/renames outside that allowlist and uncertain diffs select full. Component groups are useful locally but are not yet an unproven substitute for full CI on code changes.

## Latest versions and external boundary

CI uses `python-version: '3.x'`, `node-version: 'latest'`, `check-latest: true`, and `ubuntu-latest`. Resolved versions are recorded per run; no older local runtime is imposed. Action releases are checked against current upstream releases when implemented.

The current Dispatcher upstream is `whichguy/plan-orchestrator`, default branch `main`, verified at `86cf08050d0d3eb402ce29e687652d3d53600d5c` during planning. It is private, and skill-craft currently has no repository Actions secrets. Therefore the latest-package qualification is an explicit local release check, with a reusable command for a future authenticated CI environment. Hermetic CI retains frozen compatibility fixtures; they do not claim to qualify the latest installed dependency. No new credential or repository protection setting is introduced.

The user authorized commit, merge and push. The release procedure will wait for complete candidate CI and verify main afterward; this is an executed release gate, not a claim that server-side branch protection has been enabled.

## Test design

Use executable fixtures for selection union, shard coverage, missing files, failure continuation, timeout cleanup, no-execution listing, external output placement and source identity. Test PR routing on docs, source, shared infrastructure, generated payloads, renamed/deleted paths and missing-base conditions. Preserve meaningful runtime tests during fixture extraction and compare discovered test IDs before/after, except the deliberately moved predicate. Full GitHub CI supplies complete regression evidence; scoped local checks are labeled separately.

The prior independent plan review raised risks around ambiguous candidate identity, moving dependencies, receipts in the checkout and overoptimistic path selection. The plan addresses these with PR merge-ref testing plus exact-main verification, explicit dependency receipts, external report paths, and conservative full routing. Its suggestion to keep old runtime majors is rejected because it conflicts with the user's latest-version requirement.

## Execution evidence

- Baseline `8744d8fed103fa5eebe8b8ce49912d41fbb634ec`: smoke (28 core plus ten ShipLoop entries) and plugin parity passed. HEAD/tree and checkout unchanged; only declared Python bytecode appeared. Python 3.14.7, Node 25.9.0, Bash 3.2.57. No retries. Logs: `/tmp/skill-craft-ci-implementation-20260922.r9uzgE/baseline-logs`.
- Implemented one 131-entry hermetic catalog: 28 core, 101 ShipLoop, one source E2E apparatus aggregate and one historical experiment. Component unions deduplicate; three ShipLoop shards use static duration estimates.
- New CI policy verification passed all nine tests with stable source hashes; independent CI review found no actionable issues.
- Fixture extraction preserved every test method except the deliberate action-walk-to-contract predicate move. The strengthened predicate uses valid material-cycle receipts.
- Release qualification requires the refactored suites, runner/boundary checks, current-Dispatcher qualification, complete PR candidate CI, and complete main CI. Retained GitHub run artifacts and the delivery PR report are the final evidence; the baseline above is not candidate qualification.
