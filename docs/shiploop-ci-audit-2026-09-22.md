# ShipLoop testing audit — 22 September 2026

Historical audit snapshot. The resulting implementation is described in the [test guide](../test/README.md) and [delivery plan](shiploop-ci-organization-plan-2026-09-22.md). Counts and CI policy below refer to the audited revision.

**Keep the existing runner architecture, make qualification explicit, and reorganize tests around the boundary each one protects.** The smoke/full split works mechanically. The larger problems are incomplete automatic regression coverage, several meanings of “smoke,” missing source-harness checks in “full,” and expensive fixtures whose responsibilities are hard to see.

**Version policy, per the user's clarification: use latest stable tools, CI runtimes and skill dependencies.** Bring CI forward; do not downgrade the local environment to its older configured versions. Record the versions and package revisions resolved by each run so failures can be reproduced. Recording what ran does not constrain later runs to that version. Historical compatibility fixtures are a separate test subject and cannot substitute for testing current dependencies.

This is an audit and proposed organization, not a change to CI policy or test behavior. Source: skill-craft `66dd4ffea2e2bd991fe3ae205df256c9e05bd455`. GitHub runs were inspected live. The existing untracked `.worktrees/` and unrelated planning audit were left untouched. Counts below describe **constituent inventory entries: core commands plus expanded ShipLoop entries, not individual test cases or coverage percentages**. The root aggregate dispatches 29 commands; its last command expands to either 10 smoke or 101 full ShipLoop entries.

During verification, another task advanced the shared checkout to `8744d8fed103fa5eebe8b8ce49912d41fbb634ec`. The CI workflow, root runner, ShipLoop inventory and live suite catalog are unchanged between those revisions. Test results below qualify the frozen audit revision only; the newer runtime/fixture changes were not retested here. Repository source links point to the audited revision for accurate line references.

## What runs today

| Selection | Actual contents | Where it runs automatically | Meaning of a pass |
|---|---|---|---|
| Focused file | One explicitly selected test module | No automatic change-based selection | Its assertions passed |
| `core` | 28 commands, including all four Ask-Agent suites, packaging, installer and Improve checks | Included in routine smoke and manual full CI | Broad deterministic core checks |
| ShipLoop `--smoke` | 10 of 101 ShipLoop inventory entries | Through the repository smoke aggregate | Selected navigation, callback and boundary checks |
| Repository `--group smoke` | All 28 core commands plus those 10 ShipLoop entries | Every PR and every push to `main` | 38 registered entries passed; partial regression signal |
| `--group shiploop` | All 101 ShipLoop entries; one action walk | Only as three shards in manually requested full CI | Registered ShipLoop deterministic regression |
| `--group all`, also the local default | Core plus complete ShipLoop inventory: 129 entries | Manual CI `tier=full` uses equivalent core + three shards | Complete **registered** hermetic inventory |
| E2E harness `check_suite.py --suite all` | Source harness, game oracles, workflow evidence and regression controls | **Absent from root full CI**; copied-package mock subset is in core | Offline apparatus correctness; no model or hosted application proof |
| Installed/native/live qualification | Selected host, installed package or real model/application boundary | Explicit opt-in paths | Only the host and boundary actually exercised |

Local and GitHub are execution locations, not competing test levels. Both already use the same root runner. GitHub additionally runs plugin parity and tracked-file guards; invoking the local runner alone does not perform that entire CI procedure. The current CI platform is Ubuntu 24.04, Python 3.12, Node 22, with 60-minute job limits.

Sources: [run-all.sh — canonical core selection](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/run-all.sh#L58), [shiploop.test.sh — inventory and smoke selector](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/shiploop.test.sh#L8), [ci.yml — triggers and matrix](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/.github/workflows/ci.yml#L4). The [complete inventory snapshot](shiploop-ci-inventory-2026-09-22.csv) records membership, shard and direct command for every registered entry.

The ten ShipLoop smoke entries are `no-model-launch`, `navigator-v3`, `navigator-v4`, `stopped-improve`, `v4-consumers`, `packet-bounds`, `navigator-dry-run`, `chain-async`, `graph-driver` and `graph-trace`. Root README still says six; the test README diagram also says six although its prose correctly says ten. Use runner output as the inventory authority.

## Findings that change the decision

**1. Green routine CI does not qualify the full candidate.** At the audited HEAD, [run 35739719058](https://github.com/whichguy/skill-craft/actions/runs/35739719058) passed smoke in a 2m50s job. The inspected successful [full run 35685012276](https://github.com/whichguy/skill-craft/actions/runs/35685012276) belongs to older `43d2a4b`, with ShipLoop jobs of 26m01s, 41m58s and 19m54s. It is useful historical evidence, not full qualification of the current HEAD.

There is a concrete counterexample: the same reported source revision `b992183` passed [PR smoke 35682885555](https://github.com/whichguy/skill-craft/actions/runs/35682885555) but failed [manual full 35683097772](https://github.com/whichguy/skill-craft/actions/runs/35683097772). Six offline native-pilot adapter tests failed with “fresh managed start packet has no helper context-check command.” The later full run passed after repair. This supports adding dependency-aware component coverage; it does not establish that smoke itself is broken.

**2. “Full” currently excludes part of ShipLoop's test infrastructure.** The source E2E harness has its own comprehensive no-model runner, but neither root aggregate invokes it. Core does execute the harness's mock group from copied, read-only plugin payloads; that protects relocation and package binding. Keep that check and add the source apparatus to full qualification. [Installed invocation — copied-package mock](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/installed-skill-invocation.test.py#L69), [check_suite.py — apparatus groups](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/skills/shiploop-e2e-audit/harness/check_suite.py#L14).

**3. CI qualification has no enforced server-side gate today.** `hermetic` aggregates the selected tier correctly and fails unless all selected jobs succeed, but its name is identical for smoke and full. The live branch-protection API returned `Branch not protected`; repository rulesets returned `[]`. There is no scheduled full run or tag trigger in the workflow. Treat test reporting and merge/release enforcement as separate decisions. Do not assume adding a required check named `hermetic` would require full regression.

If full regression becomes a PR requirement, run it through an eligible PR/push event. Current GitHub documentation says manually dispatched workflow jobs do not satisfy PR required checks even when they target the head commit. Its documentation also explains why an always-running aggregate must inspect dependency results when jobs can fail or skip. [GitHub — required status checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks).

**4. There is no convenient middle tier.** Ask-Agent has four focused files but no named component selector. Cross-skill composition is spread across the ShipLoop inventory. The historical failure demonstrates a ShipLoop/Ask-Agent adapter incompatibility that smoke missed; it does not establish which side introduced the incompatibility. Component selection should include dependent consumers, not just files under the changed skill.

**5. Live “smoke” is a different, much larger operation.** The live catalog has seven names: `launch-smoke`, `planning-smoke`, `ttt-full`, `checkers-full`, `battleship-full`, `games-full`, and `salesforce-checkers-full`. Launch smoke is two independent intake prefixes; planning smoke is one prefix through plan-improve. Each case permits up to 7,200 seconds and 1,000 turns. These are live workflow probes, not the three-minute CI smoke.

The game catalog reuses the three game chains in `games-full`; do not execute both the individual chains and aggregate as if they were distinct coverage. The runner deliberately accepts only one selected case per launch, requires review before another case, and requires a qualified predecessor for incremental features. Partial smoke cannot become a product baseline. Completed full builders still need independent candidate-bound hosted verification. [suites.json — catalog](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/skills/shiploop-e2e-audit/harness/suites.json#L3), [run.py — single-case and verification gates](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/skills/shiploop-e2e-audit/harness/run.py#L1387).

## Are the tests heavily overlapping?

**There is substantial overlap in exercised machinery, but no evidence that the top-level runner accidentally repeats whole suites.** The three shards partition the same canonical inventory into 34/34/33 entries. Their union is tested, as is the single action-walk rule. In the inspected ShipLoop families, importing another test module reuses fixtures; it does not run that module's test methods.

| Overlap | Assessment | Recommended treatment |
|---|---|---|
| Smoke versus full | Smoke is intentionally a subset of full | Run focused/smoke for feedback and full at a qualification boundary; a full run need not execute smoke a second time |
| E2E `mock`, `workflow`, `games`, `regressions` | These named groups overlap literally | Run `--suite all` once for qualification; named groups are diagnostic selections |
| Source harness versus copied-package mock | Similar scenarios, different failure boundary | Keep both: source correctness versus payload relocation, binding and read-only operation |
| Legacy action walk versus full runtime | Different protocol generation and runtime composition | Keep representative walks; do not delete one based on its name |
| Navigator v1/v2, v3 and v4 | Different supported state, recovery and reconciliation behavior | Keep version-specific coverage while those versions remain supported; explicitly separate compatibility tests |
| Standalone Improve, actual Improve CLI, stopped Improve | Direct importer versus real command transport versus cancelled/incomplete settlement | Keep distinct ownership; share fixture construction where useful |
| Chain lifecycle, chain async, chain planning context | Lifecycle/order versus real callback contention versus planning provenance | Keep the boundaries; reduce repeated setup before reducing assertions |
| Ask-Agent workspace versus delivery | Helper workspace safety versus caller patch/cherry-pick integration | Keep separate; share temporary Git-repository utilities |
| Ask-Agent managed harness versus workspace | Synthesized host-trace/evidence validation versus actual helper state | Keep the distinct validators; a multi-host fixture pass is not live multi-host proof |
| Ask-Agent worktree harness versus current helper tests | Historical U18/W1 experiment verifier rather than the current helper | Move to an explicitly named experiment-regression group if routine budget needs trimming; retain its unique controls |
| Improve package shell suite versus managed-controller suite | Copied bundled runtime versus in-memory managed-phase routing | Keep both; neither recursively executes an upstream test suite |

For example, `test_recovery_isolation` belongs to three E2E groups, and `test_trace_corpus` to two. `check_suite.py --suite all` discovers each test module once, so this is a user-command pitfall rather than an existing aggregate duplication bug. [Group definitions](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/skills/shiploop-e2e-audit/harness/check_suite.py#L14).

The strongest structural consolidation candidate is **test fixtures importing other test cases**. Chain lifecycle and planning-context manually create `ChainIntegrationTests`; chain-async creates a lifecycle test case; v4 consumers instantiate planning-context fixtures. Extract shared construction and cleanup into a non-test support module with explicit ownership. Keep per-test disposable repositories and process cleanup. Sharing helper code does not justify sharing mutable workspaces. [Lifecycle setup](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/shiploop-chain-lifecycle.test.py#L84), [planning-context setup](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/shiploop-chain-planning-context.test.py#L41), [async fixture](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/shiploop-chain-async.test.py#L16), [v4 consumers](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/shiploop-v4-consumers.test.py#L28).

Ask-Agent's worktree harness imports the historical `verify-w1.py` experiment verifier. Its unique redaction, ordering and archival checks remain useful, but calling it current helper coverage obscures ownership. Workspace, delivery and managed-harness each have different assertions and isolated repositories. [Historical verifier binding](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/ask-agent-worktree-harness.test.py#L21), [delivery integration](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/ask-agent-delivery.test.py#L225), [managed evidence validator](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/ask-agent-managed-harness.test.py#L271).

There is also an opportunity to **reconceive expensive negative cases**. Several action-walk and knowledge tests bootstrap the entire earlier workflow before testing one late rejection. Preserve a small number of authentic public-CLI journeys, then pilot isolated, validated fixture builders for targeted mutations. Do not replace identity-sensitive Git/worktree cases with arbitrary serialized snapshots. Prove the replacement catches the same deliberate faults and retains cold-recovery, ancestry and cleanup assertions before removing an old case. [Action-walk bootstrap examples](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/shiploop-action-walk.test.py#L2587), [knowledge bootstrap](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/shiploop-knowledge.test.py#L140).

A small concrete split is `test_twelve_material_cycles_do_not_converge`: it checks an in-memory predicate but inherits the action-walk fixture's temporary Git initialization. Move pure predicates into a cheap unit group; retain real Git and public processes for assertions about those boundaries. This illustrates mixed test responsibilities, not a measured explanation of the largest runtime. [Predicate case](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/shiploop-action-walk.test.py#L2654), [inherited setup](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/shiploop-action-walk.test.py#L92).

Observed full-run hotspots, from `43d2a4b` rather than current local timings:

| Suite | Individual tests reported | Runtime |
|---|---:|---:|
| action-walk | 13 | 17m55s |
| chain-lifecycle | 49 | 13m23s |
| planning | 28 | 12m41s |
| knowledge | 4 | 6m49s |
| managed-walk | 1 | 4m24s |

Action-walk and chain-lifecycle are both in shard 2. Current sharding balances entry counts rather than measured duration. Rebalancing can reduce elapsed CI time without reducing coverage; it does not reduce total work. Fixture redesign may reduce total work, but savings and equivalent fault detection still need an experiment. These timings are measurements of one run, not a stable benchmark.

The redesign rule should be: **give each requirement one primary test owner at the cheapest layer that can detect its failure, then add a small number of tests across real boundaries.** Exhaustive malformed receipts belong near receipt validation; actual subprocess argument transport belongs in CLI tests; worktree replacement and commit ancestry require real Git; asynchronous callback contention requires concurrent processes; parent notification requires a native host. A full lifecycle should exercise the composition, not repeat every malformed-input permutation. Consolidation is justified when two cases have the same subject, setup boundary, fault and assertion—not merely the same feature name.

## One consistent organization

Use three independent labels: **scope** (focused, smoke, component, full), **boundary** (deterministic, installed package, native host, live application), and **location** (local or GitHub). Avoid making “local” a synonym for unit tests or “CI” a synonym for full regression. This follows the useful distinction between test size/resources and test purpose; Google's size taxonomy specifically emphasizes observable resources and isolation. [Google — Test Sizes](https://testing.googleblog.com/2010/12/test-sizes.html).

| Proposed tier | Purpose | When | Required outcome |
|---|---|---|---|
| Focused | Fast feedback on a changed behavior | During implementation | Selected cases and failures reported |
| Smoke | Representative critical boundaries with a measured short budget | Every PR | Explicit partial pass; suggested budget under five CI minutes, then calibrate from history |
| Component + consumers | All affected skill tests plus its callers/adapters | Relevant PR changes | For Ask-Agent, include ShipLoop handoff/native-pilot adapter tests |
| Full hermetic | All registered deterministic checks, including source E2E apparatus | Main qualification and release candidates; relevant PRs until component routing is proven | Exact candidate identity, complete inventory, no required skips |
| Host/live qualification | Installed package, parent return and generated/deployed behavior | Explicit supported-host or release claim | Host/model/package identity, observed completion, independent product evidence where required |

Start with a small responsibility map in the existing runner, not another framework. Each entry needs an ID, command, owned behavior, boundary, smoke/component/full membership and optional host/resource prerequisites. Generate readable membership and counts from that map. A suite claiming full coverage must reject an unclassified new test entry or explicitly classify it as a fixture/helper/opt-in experiment.

A component command should select a union of entries, so `ask-agent + shiploop-composition` runs their shared entries once. Keep a separate record when deliberately exercising a source package and a copied or installed package: different subjects are not duplicate execution.

Each retained result should record requested tier, selected entries, completed/passed/failed/skipped/unrun entries, per-entry duration, source SHA/tree and any external package fingerprints. Preserve failed attempts when retrying. Capture logs and summaries as GitHub artifacts; GitHub provides artifact retention for test outputs without adding another service. [GitHub — workflow artifacts](https://docs.github.com/en/actions/tutorials/store-and-share-data).

## Associated skills

| Skill or dependency | Current coverage | Missing qualification or organization |
|---|---|---|
| Ask-Agent | Four full deterministic suites already run in core, hence every smoke run | Named component selector and downstream ShipLoop adapter coverage; native return still needs per-host evidence |
| Improve | Core shell/plugin tests plus direct bridge, real CLI and stopped-result tests in ShipLoop | One visible composition group; distinguish synthetic review judgments from actual model review quality |
| Backchain / Plan Dispatcher | External repo `/Users/dadleet/src/backchain`, clean `86cf080`; `make test-fast` is its complete deterministic suite, `make test-dispatcher` its 13-suite focused selector | No `.github/workflows` at the inspected revision; skill-craft mostly tests frozen Dispatcher fixtures, not this installed checkout |
| ShipLoop E2E Audit | Complete standalone offline apparatus runner; copied-package mock in core | Add source apparatus to full qualification; retain separate live campaign and hosted verifier |
| Test Runner | Local non-Git delegation skill selects and runs caller-specified commands | It is not another suite or proof that native parent delivery works across hosts |

The selected Ask-Agent source is current skill-craft, whereas Dispatcher v1/v2/v3 under `test/fixtures` are compatibility subjects. A passing bridge test cannot qualify an arbitrary installed Dispatcher update. Add an explicit compatibility qualification against the selected external package when it changes, recording both identities. Do not replace pinned regression fixtures with ambient dependencies.

For normal current-product qualification, resolve the latest selected dependency explicitly and test that package. Historical fixtures may stay in a clearly labeled compatibility group only while an old-state migration or compatibility promise needs them; retire obsolete contracts and their cases together. Do not keep an old dependency as the default just to preserve passing tests.

Current ShipLoop Improve delegation uses Ask-Agent's consumer-owned workspace route. Its skill documentation describes bounded Codex-native pilot evidence; helper-managed fixtures do not qualify that route on every host. The external Dispatcher's former live harness also refuses fresh qualification of current managed-worktree behavior. Keep host-specific claims explicit. [Ask-Agent — composition boundary](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/skills/ask-agent/SKILL.md#L66), [native Improve pilot](https://github.com/whichguy/skill-craft/blob/66dd4ffea2e2bd991fe3ae205df256c9e05bd455/test/experiments/ask_agent_improve_native/README.md#L36), [Backchain Makefile](../../backchain/Makefile#L34).

## Recommended changes, in order

1. **Adopt: use latest runtimes and fix naming/inventory visibility.** Update root/test README counts; label `smoke` and `full-hermetic` distinctly in job summaries; keep any required gate name stable until its policy is deliberately changed. Describe live prefixes as `live-launch-probe` and `live-planning-probe` in documentation, retaining current CLI names for compatibility. Files: `README.md`, `test/README.md`, `.github/workflows/ci.yml`, harness README. Replace CI's older runtime selectors with latest stable channels and update runner-policy assertions accordingly.
2. **Adopt: close the full-suite omission.** Register source `check_suite.py --suite all` in full qualification; retain copied-package mock. Extend inventory tests to cover its registration and failure propagation. Files: `test/run-all.sh`, `test/test-groups.test.py`, test docs.
3. **Adopt: make qualification happen predictably.** Run full on main pushes as a regression detector and require an exact-candidate full receipt for release. For affected PRs, require full initially; pilot smaller component unions only after their dependency map is reviewed. Include source skills, generated payloads, shared runtimes, fixture adapters and runner/workflow edits in routing. Unknown shared changes fall back to full. A post-merge main run is not a pre-merge gate; blocking merges requires separately configuring PR protection and an eligible full-check event.
4. **Pilot: rebalance full shards from measured duration.** Preserve exact partition/uniqueness checks. First separate the two largest shard-2 entries; then measure several runs. Avoid continuously changing shard allocation from one noisy sample.
5. **Pilot: extract shared fixtures and narrow expensive negative cases.** Begin with one lifecycle/knowledge cluster. Compare old and new cases on targeted faults, state isolation, process cleanup and runtime. Retire only cases whose unique detection responsibility has a verified replacement.
6. **Defer: broad deletion, a new test framework, or routine live-model CI.** Current evidence supports clearer ownership and selective simplification, not wholesale removal of historical protocol or package-boundary coverage. Live model/hosted tests have different costs, credentials and oracles.

For step 3, the smallest main-push policy change is the matrix condition in `ci.yml`: select full when `github.event_name == 'push'` **or** manual `tier == 'full'`, under the existing main-only push trigger. Update `test_ci_defaults_to_smoke_and_full_requires_explicit_manual_selection` to reflect the new policy. PR component routing and server-side enforcement are subsequent changes, not implied by that single edit.

The runtime-selector portion of step 1 is this proposed change in `.github/workflows/ci.yml` (not applied by this audit):

```diff
-    runs-on: ubuntu-24.04
+    runs-on: ubuntu-latest
@@ Python setup
-          python-version: '3.12'
+          python-version: '3.x'
+          check-latest: true
@@ Node setup
-          node-version: '22'
+          node-version: 'latest'
+          check-latest: true
```

Use the runner-image change for both jobs. GitHub's `ubuntu-latest` is its managed latest image channel. Python's `3.x` resolves the latest stable Python 3 release; Node's `latest` resolves its latest release rather than selecting an older LTS major. Keep action releases current as well. Update `test_ci_preserves_a_fail_closed_aggregate_check`, which currently asserts the old Python/Node values. [setup-python — version ranges and latest checks](https://github.com/actions/setup-python/blob/main/docs/advanced-usage.md), [setup-node — supported version syntax](https://github.com/actions/setup-node/blob/main/README.md#supported-version-syntax).

## Commands and evidence limits

Run from the repository root:

```sh
# Same deterministic selection as routine CI
bash test/run-all.sh --group smoke
bash scripts/sync-plugin-views.sh --check
git diff --exit-code
git diff --cached --exit-code

# Current registered full deterministic inventory
bash test/run-all.sh --group all

# Additional source E2E apparatus, currently outside that inventory
python3 -B skills/shiploop-e2e-audit/harness/check_suite.py \
  --suite all --skill-root "$PWD/skills/shiploop"

# Enumerate before choosing any optional installed-host operation
bash test/run-integration.sh --list
```

Full CI shards are an alternative scheduling of the full ShipLoop inventory; do not run all three shards after the serial full runner. The same applies to `check_suite all` versus its overlapping named groups.

Fresh local verification used a detached, isolated checkout of `66dd4ff`, tree `62505aa2d2fb8909a34e32333f1a667443645ef1`. HEAD, tree and clean status matched before and after. Only permitted ignored Python bytecode was generated. Local tools were Python 3.14.7, Node 25.9.0 and macOS Bash 3.2.57; those are observed versions, not a claim that each was the newest available release. No runtime was downgraded or upgraded for this audit.

| Fresh check | Result | Evidence |
|---|---|---|
| Repository smoke | PASS; all 28 core + 10 ShipLoop entries; 6m43s | [Smoke log](/tmp/shiploop-ci-audit-20260922.Z8SpTm/logs/01-smoke.log) |
| Generated plugin parity | PASS | [Parity log](/tmp/shiploop-ci-audit-20260922.Z8SpTm/logs/02-parity.log) |
| Source E2E apparatus `all` | PASS; 332 tests in 24 modules; 7m09s wall time; zero failures, errors, skips or expected failures; zero model calls | [Machine receipt](/tmp/shiploop-ci-audit-20260922.Z8SpTm/harness-all/result.json), [raw log](/tmp/shiploop-ci-audit-20260922.Z8SpTm/logs/harness-all.log) |
| Source and output guards | PASS; same source identity; no undeclared outputs | [Identity evidence](/tmp/shiploop-ci-audit-20260922.Z8SpTm/logs/06-post-harness-identity-and-receipt.log), [output guard](/tmp/shiploop-ci-audit-20260922.Z8SpTm/logs/07-generated-output-guard.log) |

No retries were needed. The source apparatus result strengthens the recommendation to register it; it is not live E2E evidence. No full 129-entry local regression, live model campaign, native-host qualification or hosted deployment is claimed by this audit. External Backchain entrypoints were inspected, not executed. Raw local logs are retained in the temporary audit directory; the recorded outcomes and GitHub run links above remain in this report.

The 129-row inventory was checked for unique IDs and 38 smoke members; local document links resolve. An independent reviewer checked the main findings and proposed policy. Tables and links are authored as Markdown; a rendered preview was not inspected.
