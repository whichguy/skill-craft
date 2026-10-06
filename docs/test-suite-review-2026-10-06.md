# skill-craft test review: phasing, sizing, gaps and the E2E ladder, 2026-10-06

Status: **interim**. Output of a read-only workflow (a serial measurement of all 108 suites, the CI history and tier map, the E2E ladder, six
subsystem reviews, one synthesis, three adversarial reviews and a revision: 28 findings applied, 6 rejected). Measured per-suite seconds are in
`docs/experiments/test-suite-review-20261006/suite-seconds.json` (single local runs on a shared 18-core Mac, not CI numbers); the reviewers'
findings and the ten decisions are in `review-evidence.json` beside it. No model-backed call was made and no credits were spent.

## Addendum A: what happened to the Google Apps Script case after this review was written (same day)

1. The audit harness's `check` for `battleship-create` was refused at its freshness gate (`required-package-tree-is-missing`): the gate still
   looked for the old per-skill plugins. Fixed in `c27081e5` (19 tests, all failing first); the real gate then printed `ready: true` on launch.
2. The launch then ended at once with exit 2 and `harness-or-environment-error`: **the real Grok profile is not authenticated**
   (`grok models` prints "You are not authenticated."; `~/.grok/auth.json` was rewritten at the launch attempt, probably a failed token
   refresh). The harness gave no message for it, and no builder ran, so no credits were spent and nothing was deployed. Retained evidence:
   `/Users/dadleet/e2e-runs/20261006/gas-battleship-audit/battleship-create/` (its result and manifest). The same login also feeds the main
   harness's Grok host (a symlink to `auth.json`), so every Grok run is blocked until `grok login` is done interactively by the owner.
3. The audit harness's preflight (`run.py check`) does not test authentication; a `grok models` probe in it would refuse before any output
   directory is created. Candidate improvement, not built.
4. Decision 1 below is now the live question: the audit route needs a Grok login and, for a full verdict, a deployment, a verifier and a
   Battleship browser mapping; the offline single-player case in the main harness on Claude needs none of those.

---

## The review

Read at main 219c1de6. The worktree moved to 81e0502f during the work; that move changed only the E2E harness and a journal. Disputed facts were re-checked in the worktree at 81e0502f. No model-backed call was made and no credits were spent. Local seconds come from one serial run of all 108 suites on a shared 18-core Mac (load 6.3 at start, 3.5 at end). They are not CI numbers. GitHub per-suite seconds come only from `Ran N tests in X s` lines in the run logs. Node and bash suites print none, so their GitHub seconds are unknown. Figures marked "estimated" are my arithmetic from measured parts and are not verified.

**Your clarification comes first.** The live E2E harness has no Google Apps Script Battleship case.
- `test/shiploop_e2e/cases.json` `battleship` is a Node.js HTTP server graded by `node --test` and live requests. `battleship-scoring` follows it.
- The Battleship run that wrote the 08:23 row today (Claude Sonnet 5.5, plugin 1.22.0, $6.54, 238 turns, `/Users/dadleet/e2e-runs/20261006/v1220-battleship-sonnet`) built the Node version. It does not answer your question.
- Closest to what you describe: the documented open experiment in `docs/shiploop-composition-state-experiments-2026-09-26.md` ("One full ShipLoop run from 'Build a Battleship game' on Apps Script"). It was never run.
- Other pieces exist but none is that case. Rubric-eval scenario S01 (`skills/rubric-eval/suites/architecture-v4/scenarios.json`) is the single-player request for the GAS and SF runtimes, and it scores plans, not products. `battleship-create` in `skills/shiploop-e2e-audit/harness/scenarios.json` is runnable but differs: two local players, hosted deployment through the MCP, three chained steps, Grok only.
- Section 6 covers it.

---

## 1. How the tests are phased today

| Tier | Trigger | What runs | Measured cost |
|---|---|---|---|
| Quick | Every push to main whose `before..HEAD` holds no `Skill-Craft-Release` commit | 16 fixed suites plus changed-path matches (kept only if recorded seconds are at most `QUICK_MAX_SECONDS` = 120; a missing entry counts as 0.0). 4 CI jobs. Observed 16 to 20 suites, worst 33 (run #463). | CI wall median 3.8 min (n=29, 1.9 to 11.5). Since the audit fixes (from ebc2d25d, n=8): median 3.0 (2.2 to 4.0). Quick job test step median 179 s, 126 s since the fixes. The 16 fixed suites sum to 115.1 s locally (loaded machine; the audit's 124 s was for a 17-suite selection, not this baseline). |
| Full | Push range contains a release commit | All 108 suites in 5 groups: core 39, shiploop-1 (chain-lifecycle alone), shiploop-2 35, shiploop-3 31, e2e-apparatus 2. 8 CI jobs. | Wall median 18.6 min (n=11, 17.7 to 32.7). The 32.7 is run #471, where one job was rerun. |
| Local-only groups | manual | all (108), shiploop (67), ask-agent (9), shiploop-composition (16) | Local serial full run: 3524.7 s (58.7 min), 108 of 108 passed, 0 guard events. |
| Opt-in integration | manual `test/run-integration.sh` | cursor-imports, marketplace-claude/grok/codex, codex-ask-agent, current-dispatcher, and the three live E2E targets. `ci-policy.test.py` asserts CI never runs it. | Unknown. The three E2E targets cost money. |
| Live E2E | manual | `test/shiploop_e2e` (9 cases) and the audit harness `skills/shiploop-e2e-audit/harness` | See section 6. |

PR and dispatch triggers exist but were last used 2026-09-25 and 09-23. The repo ships no git hooks.

**Full tier per job** (median minutes over 11 runs): plan 0.3, release-boundary 0.4, core 18.2 (15.1 to 19.0), shiploop-1 9.2, shiploop-2 8.3, shiploop-3 8.5, e2e-apparatus 14.6 (10.7 to 18.0).
- Core is the pole. `plan-dispatcher-mutants` alone is 576.3 s (run #462) and 631.8 s (run #469).
- The three ShipLoop shards never gate the run.

**Local cost shape.**
- 22 suites over 30 s make up 90.2% of the 3524.7 s. The top ten make up 74.0%. 67 suites ran in under 5 s.
- Slowest locally: shiploop-chain-lifecycle 985.8 s, e2e-apparatus 435.8, shiploop-chain 306.9, plan-dispatcher-mutants 276.8, chain-planning-context 147.4.

**Local seconds do not convert to GitHub seconds.**

| Suite | Local (loaded) | GitHub |
|---|---|---|
| plan-dispatcher-mutants | 276.8 | 576 to 632 (2.1 to 2.3x slower) |
| shiploop-e2e | 62.5 | about 41 |
| shiploop-chain-lifecycle | 985.8 | about 540 (546.6 in one log) |
| shiploop-chain | 306.9 | 181.3 |
| shiploop-chain-planning-context | 147.4 | 81.1 |

So I state savings in local seconds and say so. The shiploop-e2e catalog entry of 61.0 s is an estimate; three GitHub readings after the poll fix are 40.3 to 41.3 s.

**CI health** (118 main runs, #357 to #474; 119 attempts counting the #471 rerun): 9 red outcomes (8 failed runs plus #471 attempt 1).
- 4 were pins (#373 to #376), 2 real regressions (#410, #415), 2 runner environment (#421, #422: the runner's git-lfs filter broke two new tests), 1 flake (#471 attempt 1, `shiploop-progress` `test_duplicate_start_and_cooperative_stop_then_restart`, "2 != 0").
- Plan, release-boundary and the checkout guard were green in every final attempt.

**Runner time.**
- A quick run is 2.8 job-minutes at the median; a full run is 57.1. The full tier is 82% of runner minutes. Estimated at the observed cadence: about 5,600 job-minutes per 30 days (range 3,600 to 8,350 by window).
- Billable time was 0 ms on 3 sampled runs of a public repo. Account-level billing is not verified. The cost is wall time.

**What a developer waits for.** Quick in CI is about 3 minutes. The local quick check, and `release.py` plus the guarded push, are unknown. A release then costs 18.6 minutes of CI (32.7 if one job needs a rerun). Under your proceed-optimistically rule only the release wait is long.

---

## 2. Sizing verdicts

Verdict definitions, so none is a bare opinion: **Oversized** = sits on a gating pole and has a measured, defect-level cause. **Undersized** = a verified untested destructive path or oracle. **Brittle** = pins incidental detail. **Do-not-touch (DNT)** = the 2026-10-05 audit's list: release-boundary job, fixed baseline until the O9 diff check, chain suites, navigator door suites, the mutants gate (speed it up, never remove it), the E2E harness and apparatus tooling suites, `catalog_omissions`, the drift guards.

| Suite or tier | Verdict | Evidence | Action |
|---|---|---|---|
| Quick tier | Appropriately sized | Median 3.0 min since fixes. The poll fix is confirmed on GitHub (shiploop-e2e about 300 s to about 41 s). No pin red in the 98 runs after #376. | Keep the fixed baseline (O9 first). |
| Full tier | Right structure, two poles | Core 18.2 min and apparatus 14.6, against shards of 8 to 9. | Section 5: O5 and O6 together. |
| plan-dispatcher-mutants | Oversized | 576 to 632 s on GitHub, about 10 of core's 18.2 min. Each of 38 mutants reruns a whole suite. `mutate.py` has no unit test. Catalog says 420. | Audit O6 (audit-recommended; not DNT, but it changes what the gate runs). Owner go. |
| shiploop-e2e-apparatus | Oversized | 768.9 s of tests in run #469 (338 tests). Job 10.7 to 18.0 min against a 1200 s timeout. The audit measured 467 s to 103 s locally with a content-hash memo. `freeze_package` omission and changed-bytes branches have no assertion. | Audit O5, memo variant (section 5). |
| shiploop-chain-lifecycle | Large but appropriate | 546.6 s on GitHub in its own shard, off the critical path. Catalog 803 is stale high. | Do not split (audit O12 agrees). Fix the catalog entry. |
| sync-plugin-views 41.5 s, release-flow 29.0 s, native-marketplace-adapters 19.1 s, ask-agent-managed-harness 80.1 s, integration-boundaries 11.8 s (all local) | Not shown to cost a measured wait | All are under the 120 s quick bound and sit in core, whose pole is mutants. ask-agent-managed-harness is 39 s on GitHub per the audit, not 80. The audit's order says to stop after O4 to O6 and take O7 to O9, O12 and O13 only if a measured wait still hurts. | No action. Revisit after O4 gives GitHub seconds and O5/O6 land. If a 3-skill fixture is done later it must keep one hook-declaring leaf, one agents-card leaf and one script-bearing leaf: sync-plugin-views is the only guard of the exact per-host hook JSON, the `agents/` list and the pycache pin. |
| Chain, async, git, workspace, callback-contract, actual-improve-cli, keepalive, lint, test-loop, quality, store, packages, release-boundary, release-push, install-*, marketplace-run | Appropriately sized | Real-process or real-Git obligations. Every in-scope suite is under the 120 s quick bound. | Keep. |
| shiploop-capability-fixture (68 s), generalized-discovery (18.4), repeatable-experiments (11.8), local-skills, probe-decisions, UI-allocation, native-trace evaluators (about 1.4 s) | Misphased, harmless | No engine surface; not on a pole; billed 0. | Leave. |
| Live Battleship oracle (`cases.json` checks) | Undersized | Earlier input: three constructed stubs pass all four checks (not re-run here). A false check costs a paid run ($6.54, 238 turns on the last one). | `CheckOracleTest` for Battleship (section 3). |
| release-boundary (4.0 s) | Undersized | The `plugins/` prefix (A2) and skill-card version (A10) are tested. The CHANGELOG file, README inventory block, bundle version and the four host catalog prefixes have no case, and neither does the negative case (a README prose edit passes). | Case A11. |
| release.py dirty tree, install.sh name guard, release-push ancestry | Undersized (destructive paths) | Guards exist and no test names them. `release-push` `assert_blocked` checks a nonzero exit and an unmoved remote, not the reason. | Section 3 rows 3 to 5. |
| installed-skill-invocation, marketplace-package entrypoints | Undersized, small | adversarial-review, rubric-eval and shiploop-run-review are absent from both tables. `check-marketplace-packages.py` gives unknown packages a conservative recognized-script fallback, so they are not unchecked, only unnamed. | Add three rows. |
| rubric-eval | Undersized | The CLI, export, claude and codex argv, and suites v2 to v4 are never executed. | After the v2/v3 retire decision (section 7), cover v4 only. |
| Committed `baselines.jsonl` | Undersized | `scan_baseline` silently skips unreadable lines; no test reads the committed file. | One parse test. |
| Suite-count pins in test-groups (67/39/108) | Brittle | 38 commits touched the count lines between 09-22 and 10-05; 4 since 09-28. No red CI from them since #376. The audit's O10 asks to replace them with derived invariants plus a reachability check for nested experiment and apparatus entries. | O10 as the audit wrote it (section 5). Not the `< 17` bound and not the path table. |
| `assertLess(len(baseline), 17)` and the exact path table in test-groups; ci-policy `check-latest` count of 5 and `upload-artifact@v7` (it also forbids a pinned `ubuntu-24.04` runner) | Keep | The bound is the only size guard on the fixed baseline (DNT until O9). The exact table is the over-selection guard that O3 depended on. | Keep. Change the bound only in the O9 step. |
| Prose pins in ShipLoop suites: guidance (159 `assertIn` calls), actual-improve-cli (109), delegation (61), navigator-contract (large document scans, count not measured), plan-dispatcher-cli (about 30 whole sentences) | Brittle, not currently red | `assertIn` counts include non-prose asserts. Cost shows as edits, not red runs. Navigator suites are DNT. | Defer to the planning_review default flip, then consolidate (section 5). |
| `len(REMOVED_SCRIPTS) == 30` in no-model-launch; improve.test.sh version literal; `run.py` `"1.22.0"` count and `FastPlanningRecordTest` in shiploop-e2e | Brittle or misplaced, but inside DNT suites | no-model-launch is in the fixed baseline. shiploop-e2e is an E2E harness suite. The tombstone checks in no-model-launch and the script-sha256 and upstream-commit literals in improve.test.sh are real guards (the manifest is edited together with the bytes, so removing the literals makes the check circular). `FastPlanningRecordTest` holds the S-10 carve-out test and the audit-evidence test; only `gate_experiment.out` is exercised nowhere else. | Do nothing now. At the experiment-corpus move, delete only the file-existence checks and decide the S-10 test then. Owner go for any of these. |
| backchain-check counts [23, 28, 5] and 131-byte line | Keep | Only guard against silently shrinking a corpus recorded once from `lib.js`. | Keep. |
| Backchain prompts and references (17 files) | Accepted | Behavioural evals live in the private harness. | No content pins. |
| Old-version tests | Reviewed, none confirmed deletable | `row_planning_review` reads live data: 16 of 17 working-tree rows have no `planning_review` field. `upgrade_docs` is the current upgrade of the live Run Review page. The saved-protocol-3 refusal is the one-supported-version obligation itself (found in navigator-contract and navigator-v4, both DNT; the earlier "5 suites" could not be reproduced). | Keep all. Delete a test only if it accepts or migrates an old format, and name it first. |
| Duplicates: inherited re-runs in delegation (18 of 47) and knowledge (7 of 21), improve-plugin (2.4 s), skill-interop-hygiene (0.04 s), install-arbitrary-skill E6 | Duplicate, low value | About 2.6 s and 0.9 s for the inherited re-runs. improve-plugin has two unique assertions (README ships; package README lists SKILL.md). E6 has one unique bytecode line. | No action unless touched. If deleted, prove each with a one-line mutation naming the suite that goes red, and move the unique lines first. |
| dual-body-guard (2.4 s) | Contested | `docs/skill-release-checklist.md` names it as the guard. The generator already refuses external/bundled name collisions, so its external half may be redundant. Its `plugins/<other>` half is covered only by the stray-directory tests in sync-plugin-views and native-marketplace. | Fail-first test: add `skills/lennox-s40/SKILL.md` and see which suite goes red. That proves the external half only. Keep one stray-directory test whatever the result. |
| prompt-marketplace-contract (0.04 s) | Misphased | `suite_catalog.quick` on each of the 10 prompt-only leaf cards selects only skill-frontmatter, so a regression is first found on the release commit. | Add a selection rule (section 5). |
| shiploop-literal-transport (1.5 s) | Misphased | A SKILL.md edit selects 4 suites in quick, but this suite tests the init command SKILL.md documents. | Add to `_SHIPLOOP_PROMPT_IDS`. |
| Selection holes | Misphased | Edits to `shiploop_navigator.py`, `shiploop_protocol.py` or `shiploop_chain.py` do not select experiments-shiploop-chain-native-pilot (audit O11). An edit to `skills/ask-agent/scripts/ask_agent_workspace.py` selects 28 suites: the 16 baseline, 4 ask-agent, and 8 from the hub fallback (the hub set has 9; planning-handoff is already in the baseline). | O11 minimal. Ask-agent routing: measure first (section 5). |
| `_DURATION_SECONDS` | Stale and incomplete | 46 of 108 suites have no entry. `_light()` reads missing as 0.0, while the shard planner reads 60 s (7 unlisted ShipLoop suites: 420 s assumed against 48.9 s measured locally). Examples (catalog, then local): run-review 0.2 then 13.1; test-loop 3.0 then 46.5 (GitHub about 31.6 at 45 tests); workspace 19.4 then 88.3; mutants 420 then 277 local but 576 to 632 on GitHub. | O4: GitHub seconds only; one default for missing entries. |

---

## 3. Scope gaps

**Proposed.** Each has a demonstrated miss or a verified untested destructive or oracle path. "Fail-first" says how the new test is proven red; a test that passes on main must be shown red by the named mutation in a scratch copy.

| # | Gap | Test (name, where) | Fail-first |
|---|---|---|---|
| 1 | No Apps Script Battleship one-shot case in any harness the owner can run cheaply. | Section 6. | n/a |
| 2 | Battleship oracle uncalibrated. | `CheckOracleTest` in `test/shiploop-e2e.test.py`. A tiny good product on a free port passes every check. One-line mutants fail the right check: wrong result enum, `gameOver` never true, 500 on `/api/new`, wrong page title. Same shape for the GAS case once it exists. | Red today if the three-stub claim holds (not re-run). |
| 3 | `release.py` on a dirty checkout; its failure handler runs `git reset --hard` and `git clean -fdq`. | `test_release_refuses_a_dirty_checkout` in `test/release-flow.test.sh`: untracked file, edited tracked file and pending note give exit 1 with "checkout must be clean"; HEAD and both files unchanged. | Pass-first. Mutation: remove the clean-checkout raise. |
| 4 | `install.sh` unsafe `--skill` names (`../escape`, `Upper`, 65 characters). The name becomes a path that `--uninstall` removes. | In `test/install-arbitrary-skill.test.sh`: exit 64 with "Invalid --skill value" for install and uninstall; a sentinel at `$HOME/.claude/escape` untouched. | Pass-first. Mutation: drop the name regex. |
| 5 | `release-push.py`: a candidate that does not descend from `--expected-base` (first precondition in the release checklist). | `test_candidate_must_contain_the_base` in `test/release-push.test.py`, with a parentless `git commit-tree` candidate. Assert the reason text, since `assert_blocked` checks only a nonzero exit and an unmoved remote. | Pass-first. Mutation: remove `merge-base --is-ancestor`. |
| 6 | `freeze_package`: credential-shaped omission and changed-bytes error. | Direct test in the harness `test_run.py`: a clean file saved at 0444; a credential-shaped file omitted with reason `credential-shaped-input`; a byte changed after hashing raises "selected skill changed while freezing inputs". Lands before O5. | Pass-first. Mutation: remove the omission branch. |
| 7 | `check-release-boundary.py` branches with no case. | Case A11 in `test/release-boundary.test.sh`: CHANGELOG, README inventory block, bundle version and each of the four host catalog prefixes fail naming the path; a README prose edit outside the markers passes. | Pass-first. Mutation: drop CHANGELOG from `GENERATED_FILES`. |
| 8 | `metrics.SHIPLOOP_COMMAND` misses 10 of 23 CLI verbs: view, chain, backchain-check, hook-status, graph-dry-run, delegation, status, report, context, halt (`lint-mode` is counted under `lint`). Refusals through them are uncounted. | In `test/shiploop-e2e.test.py`, derive verbs from `shiploop --help`; each must match the regex or sit in a named read-only list. Mirrors `test_direct_subcommand_allowlist_matches_the_current_shiploop_cli`. | Red today. |
| 9 | Progress observer start has no soft-failure test. | `test_unavailable_observer_is_soft` in `test/shiploop-progress.test.py`. Test-only: patch Popen to a process that never publishes and patch the monotonic clock. Assert `start()` is False, `ensure()` prints the unavailable line, `next` exits 0, `state.md` bytes unchanged. Leave the four success assertions and their diagnostics alone. | Pass-first. Mutation: return True on timeout. |
| 10 | Test-author probe: a runner whose summary appears only on stderr is not tested through `verify()`. | `test_stderr_only_summary_is_counted` in `test/shiploop-test-loop.test.py`. | Pass-first (verify joins stdout and stderr). Mutation: read stdout only. |
| 11 | `planning_review none` (1.22.0) with the chain, revise, workspace return, status/report/hook-status and ask-agent. Add before the default flip. | (a) `test/shiploop-chain.test.py` diamond run, first child binds at static-checks; (b) `test/shiploop-revise.test.py` revise at plan leaves `improve_results` empty; (c) `test/shiploop-workspace.test.py` none workspace through plan-return and return; (d) `test/shiploop-status-display.test.py` no Improve row at planning stages. | Unknown until run. Run each against a throwaway worktree of main and keep the red output before any fix. |
| 12 | Run Review: a none run whose `improve/` holds a planning child still reports "skipped by design". Fixtures `state-none.md` and `state-stage.md` are frozen. | In `test/shiploop-run-review.test.py`, build state with `navigator.new_state(planning_review=...)`. | Unknown until run; same method as row 11. |
| 13 | rubric-eval: CLI (`arm_arg`, build/export), claude and codex argv (effort and read-only flags), `make_packet_frame.py` (the planning-review plan says it breaks at the default flip). | Argv assertions in the same `subprocess.run` patch pattern the Grok test uses. Loop the consistency test over v4 only, after the retire decision on v2 and v3. | Unknown until run. |
| 14 | Hook declaration validation messages (duplicate id, bad timeout, malformed JSON, extra key). | Table-driven in `test/sync-plugin-views.test.sh`. | Pass-first. |
| 15 | S-14 person-only open-item route (a13, shipped 1.20.0); no recorded run has reached system-test since. | I have not read the a13 spec; verify against it first. Expected shape: a hermetic navigator or CLI test where a person-only item is recorded as open and the run proceeds with stdin closed. | Unknown. |

**Candidates, documented and not proposed** (no real run hit them; add when the code is touched): chain crash points after `launched_intent` and after `child_init_intent` (read, not executed), dispatcher `init` after the directory exists, and `_require_external_run`; `iterate.main` stop paths; node:test output is uncounted (rated low and medium by different reviews; only the live Node case asks for it); progress idle-timeout reason text is never asserted (the path itself runs in `test_failed_shutdown_render_still_records_stop`); output over 6000 characters (`TAIL_CHARS`); two-row probe; Until Loop done with a consumed token; `--receipt` refusals; `agents/backchain.md` router skipped by the packaging test; `review-coverage preflight --strict`; ask-agent `close` with a malformed acceptance file; `mutate.py` verdict unit tests (a prerequisite for O6, so it is in Wave 2); backchain-check cwd discovery and symlink record failures; `workspace start` forwarding of `--include-untracked` and `--exclude`; run-directory and `.lock` symlink refusal; scaffold exit 2 and 5; `run-integration.sh` arms.

---

## 4. Flake and fragility inventory

| Item | Evidence | Smallest fix |
|---|---|---|
| `shiploop_progress.start` allows 1.0 s for a spawned observer. Four tests assert success. | The only demonstrated flake: run 37428360963 attempt 1, "2 != 0". It cost a rerun and about 14 minutes of wall (32.7 against 18.6). The cause is unproven. Commit 3b246328 now prints stdout and stderr on failure; run #472 was green. Not reproduced locally at idle, 2x or 4x load. | Wait for the next failure's printed output. Do not change `start()` and do not relax the four assertions (exit 2 is also the busy-lock refusal). Add only the test-only soft-failure test (section 3 row 9). |
| `test_busy_lock_skips_without_blocking` asserts under 3 s for a cold CLI start. | Wall-clock bound; no failure recorded. | Leave. If it flakes, assert on the observable (lock skipped, process exited) rather than choosing a new bound. |
| Runner Git config leaks into new tests. | #421 and #422: git-lfs filter, "custom Git filters are unsupported". Fixed by 9e937eb0 for that suite only. improve-runtime, ask-agent-managed-harness and the review-coverage fixture do not isolate HOME or Git config. | Set `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1` in shared support. |
| Direct suite runs leave detached progress observers. | Only `run_suites.py` sets `SHIPLOOP_PROGRESS=off`. callback-contract carries a `remove_tree` retry loop for this. | `setdefault` it in the shared support modules. |
| Floating CI runtimes (python 3.x, node latest). | `ci-policy` pins them on purpose. A new major can turn CI red with no repo change. | Compare the runtime versions in the receipt before debugging a red run with no code cause. |
| run-review node tests skip when node is absent. | The suite passes with most page logic skipped. | Fail rather than skip when `CI` is set. |
| ask-agent-workspace signal and git-timeout tests. | 13 s of fixed sleeps. A global 1 s `ASK_AGENT_GIT_TIMEOUT` can fire on an earlier git call. | Poll for the marker; scope the short timeout to `worktree add`. |
| integration-boundaries `test_current_dispatcher_timeout_kills_a_term_ignoring_descendant`. | A 0.2 s deadline races the leader's startup. Its 10 s TERM grace is hard-coded in `run_with_process_group`. | Arm the deadline after the marker exists. |
| test-groups 0.1 s timeout tests. | A deadline shorter than interpreter start can pass vacuously. | The leader writes a ready file; assert it exists. |
| Other wall-clock bounds. | e2e launch under 1.5 s; apparatus `test_capture` (0.7 s child against a 0.9 s check); shiploop-chain-git FIFO under 5 s; lint stopwatches; native-pilot 20 s hold; generalized-discovery elapsed bounds. No failure recorded for any. | Assert on result fields or poll. |
| shiploop-workspace chmod 0555 tests. | No uid guard. A root runner would fail 4 tests. | Skip when `os.geteuid() == 0`. |
| Live Battleship checks use fixed ports 39171 to 39173. | Concurrent cases can collide. Live only. | Free port per check, as `seat_service.py` does. |
| `SKILL_CRAFT_PACKAGES` exported with a stale build. | Suites silently test the stale build. | Runner sets it deliberately, or `package_build` refuses a build with a different source SHA. |
| release-flow fixture (`git ls-files | xargs tar`). | A tracked-but-deleted file in a dirty tree fails it. Local only. | None needed unless the fixture is rebuilt later. |
| Apparatus timeout margin. | Suite timeout 1200 s against a worst observed job of 18.0 min. No timeout recorded. | O5 (audit: about 80% of the work). |

---

## 5. Phasing recommendations

Minutes matter less than risk here, because of proceed-optimistically. The audit's order is: O4, then O11 minimal and O10, then O5 with O6, then stop and re-decide. This section follows it. Savings are local seconds unless marked GitHub.

| Change | Effect | Audit status |
|---|---|---|
| Selection rule: any `skills/<prompt-only-leaf>/` edit selects prompt-marketplace-contract in quick. Not in the fixed baseline. | +0.04 s only when those leaves change; detection one release earlier. Putting it in `_QUICK_CORE_IDS` would trip the `< 17` pin and touch the fixed baseline. | Avoids the fixed baseline. Use the baseline route only after O9. |
| Add shiploop-literal-transport to `_SHIPLOOP_PROMPT_IDS`. | +1.5 s on SKILL.md edits; a broken documented init command is found at push, not release. | Not on the list. |
| O11 minimal: a must-select row in test-groups first. Adding native-pilot to `_HUB_SUITE_IDS` is your call. | Hub edits would add up to about 56 s (GitHub). Audit: this suite would have caught the 09-24 hub-edit breakage. | Open; coverage item, not a wait item. |
| Ask-agent helper edits: possible reroute to the ask-agent group. | Not shown neutral. Today's selection adds 12 suites (4 ask-agent, 8 hub). A reroute drops the 8 hub suites (actual-improve-cli 40.1 s, lint 37.9, keepalive 34.6 and others) and adds consumer-delivery, chain-handoff, native-pilot (not verified). | Derive before and after with `suite_catalog.quick((path,))` and add a must-select row. Do not call it neutral without that diff. |
| O10 as the audit wrote it: delete the three count assertions (67/39/108). Replace them with a derived reachability check for nested experiment and apparatus entries. | Removes the churn (38 commits). The one thing the count uniquely guards is removal of a nested entry. | Open. Keep `< 17` and the exact path table; change the bound in the O9 step, or replace it with "sum of recorded baseline seconds at most `QUICK_MAX_SECONDS`" once O4 fills the durations. |
| O4: print seconds on the runner's OK line; fill `_DURATION_SECONDS` from GitHub only. Receipts with `duration_seconds` per suite are the `hermetic-<group>` artifacts of run 37391042290 (about 89 KB total, expire 2027-01-03). Downloading needs your approval. | No cost. Removes the blind spot behind every "unmeasured" figure, the `_light()` and shard-default mismatch, and the shard rebalancing. | Open. Never refresh from Mac receipts: that would evict the ask-agent suites from quick (audit risk note). |
| O5, audit's memo variant: memoize the credential-shape check by content hash, built inside the test fixture, keyed on sanitizer identity. Land the direct `freeze_package` test first. | Audit measured 467 s to 103 s locally with 338 of 338 passing; audit estimate 766 s to about 170 s on GitHub (inferred, not measured). The first test still pays about 12.6 s. Apparatus job from 14.6 to about 4 to 5 min (estimated). Alone it does not shorten the release, because core is the pole. | Open. The apparatus suites are DNT, so keep coverage: do not swap `OBSERVER_ROOT` for a 2-file stub (unmeasured, and it makes the placement assertions vacuous). |
| O6 after `mutate.py` unit tests (SURVIVED, WRONG-REASON, stale find, killed). Pass `killed_by` as the scenario argument, keep the full baseline run, and add a solo baseline pass of each distinct `killed_by` scenario against the unmutated package. | Audit estimate: mutants 636 s to about 180 s, core about 1,081 s to about 625 s (inferred). My more conservative arithmetic: scenario mutants are about 43% of the suite's serial work (10 x 35.4 s of about 814 s), so 576 to 632 s down to about 350 to 385 s. The two are not reconciled; measured so far only on the scenarios mutants file (10 of 10 killed in 51 s wall). Decisions and exact-calls mutants (28 of 38) cannot be selected per test, as far as I found. | Audit-recommended, changes what the gate runs. Owner go. Run all 38 mutants both ways once and compare killed sets before changing CI. |
| Option: give mutants its own CI job, as shiploop-1 does for lifecycle. | Estimated release wall: today 18.6; split alone about 14.6 (apparatus becomes the pole); O5 plus split about 11; O5, O6 and split about 9 to 10 (shards become the pole). Stacked estimates. | Changes placement, not the gate's content; the group-count pin changes. Owner go; decide after O5 and O6 are measured. |
| Do not split shiploop-chain-lifecycle; do not move experiment-apparatus suites to a new tier; no fixture rewrites or retirements (section 2). | Not shown to cost a measured wait; billed 0. | Chain suites untouched. |
| Leave navigator-contract and guidance prose pins until the planning_review default flip. | No red CI from them in 98 runs; the flip will hit about 60 pinned phrases anyway. Then consolidate: table-drive the four option contracts, one shared stage list, `PROTOCOL_VERSION` instead of literal 4. | Navigator suites are DNT; the evidence does not override the audit today, and would at the flip. |
| Phase everything else as it is. | Live E2E and integration stay out of CI. | Release-boundary job untouched. |

Test additions in section 3 are mostly in full-tier suites. Their added seconds are unmeasured.

---

## 6. The E2E ladder

**Is each rung sized for its purpose?**

| Rung | Purpose | Sized? |
|---|---|---|
| hello (19-word prompt, 2 checks) | Smoke | Yes on Claude. 7.4 to 15.2 min, $3.30 to $7.33, 35 accepted actions. The two 1.19.0 runs cost $5.37 and $7.33 (1.36x); across releases 1.16.1 ($3.30) to the 1.19.0 repeat ($7.33) is 2.2x. The cause is not shown (n=1 to 2 per release; the "rises with each release" reading is marked superseded in LEARNINGS.md). Check 2 passes a no-test product on Python below 3.12. |
| battleship (Node, 4 checks) | web-service | Yes on Claude. 1.16.0: about 19 min, 353 turns, at least $4.62. 1.22.0 today: $6.54, 238 turns, at least 17.5 min (sum of 46 recorded stage entries; whole-run wall not recorded). Grok medium: 66 to 113 min, $22.66 to $35.32 (old releases). Luna: hours, blocked (cost unknown). |
| battleship-scoring | Follow-on and retention (S-11) | Last run live on 1.16.0. |
| csv-report, seat-reservations | Focused styles | One case per style, so "depth" is a rerun of one probe. csv-report never run on Claude. Duration on Claude unknown for both. |
| Breadth (3 cases) | Generality | Claude duration is extrapolated from the Node Battleship run (about 19 min, 1.16.0), not measured for these cases. Hours on Luna against the 30-minute planning ceiling. Contains no parallel-graph case. |
| parallel-graph (4 cases) | Chain route (S-1, S-2, S-6) | In no suite. Seeded or interrupted runs write no baseline row by design. Claude seeded runs: 16 to 23 min, $8.60 to $11.75. |
| Apparatus (hermetic) | Observer harness | Oversized, see section 2. |

**Baseline rows.** 16 rows are committed at both 219c1de6 and 81e0502f, and only 1 (hello 1.20.0) names host and model. The working tree holds 17: the 1.22.0 Battleship row (host claude, model claude-sonnet-5-5) is an uncommitted modification, so it is not in repository history. The other 15 committed rows are never compared.

**SPEC coverage, with live-uncovered clauses.**

| Clause | Live evidence | Gap |
|---|---|---|
| S-1, S-2 | Verdict, failures, resumed sessions on every case. | Failure counter unmeasured on Claude, the default host. |
| S-3 | None. Reviewer judgement only. | Live-uncovered by construction. |
| S-4, S-5 | `model_glue` and cancelled tool calls: full on Grok, lower bound on Codex. | Unmeasured on Claude. |
| S-6 | Kill-and-resume only on seeded chain cases (passed on 1.17.0). | No normal-case run. Claude compactions unmeasured. |
| S-7 | Peak context on Claude and Codex. | Truncations measured on Grok only. |
| S-8, S-12, S-13 | The SPEC says "review of the diff under test". | No live case on any platform card other than Node or Python. 8 of 11 cards never routed live. |
| S-9 | Checks verdict on every case. | No case with a required check that cannot be script-run. Battleship checks are protocol-level. |
| S-10 | Improve children and reviews on every case. | `--planning-review none` (1.22.0) never run live. |
| S-11 | Committed verdict and retention. | Retention last live on 1.16.0. |
| S-14 | `asked_user`, stdin closed. | Person-only open-item route (a13) never exercised. |
| S-15 | Narrative emitted and shown. | Measured, not a verdict. Claude hello rows show 0 shown of 4 to 8 emitted. |

**The Apps Script Battleship one-shot case.**

What exists:
- Platform card `skills/shiploop/references/platforms/apps-script.md`.
- The documented open experiment, the S01 scenario, and `battleship-create` (see the clarification at the top). `battleship-create` is Grok only, uses the configured Apps Script deployment MCP, and its suite `battleship-full` chains it with two follow-ups.
- Offline pieces: `gas_artifact.inspect_artifact` and `test_gas_artifact.py` (12 tests), `oracle_games.py` (five Battleship cases, needs a UI driver), 16 `fixtures/gas` directories (none for Battleship).
- A skeleton under `docs/experiments/shiploop-composition-state-20260926/battleship/fixtures/gas/`: `Code.gs` is 4 lines (`doGet` only), and in `index.html` `place()` returns `[]` and `fire()`, `computerTurn()` and `render()` are comment-only. It is a doGet, manifest and closure fixture, not a playable game.
- A hosted create has never completed in the record. The 2026-09-18 tic-tac-toe attempt hit the 7200 s cap with no product (invalid-trial). Local-only creates took 34 min 28 s and 42 min 32 s on Grok 4.6 xhigh, with no dollar figure.

What is missing:
- Any `cases.json` entry, and any GAS checks runnable without deployment.
- A known-good GAS Battleship (client logic complete) and mutants. Writing it is real effort; calibration is therefore not free.
- A way to give the main harness the MCP. `ClaudeHost.argv` passes `--strict-mcp-config` with no `--mcp-config`, and Grok and Codex run in a throwaway HOME. A hosted requirement in a main-harness prompt would be an S-14 open item.
- For the audit harness: an authorized deployment, a `--verifier`, and a Battleship browser mapping (only the tic-tac-toe mapping exists).
- Unknown: whether the MCP, a Google account or Grok credits are available on this machine, and the time and cost of any Apps Script Battleship run.

Cheapest honest way to run it:
1. **Offline, no deployment, Claude Sonnet 5.5 (recommended first).**
   - Add one `battleship-gas` entry to `test/shiploop_e2e/cases.json`: a single-player one-shot prompt ("Build Battleship in Google Apps Script", one person against the computer, no deployment).
   - Checks: files plus an `appsscript.json` web-app block; static closure (the `gas_artifact` approach); a Node vm `doGet` with stubs for HtmlService, PropertiesService, LockService, CacheService and Session; and a vm run of the assembled client script with a DOM stub (full sweep ends the game, repeat shot refused).
   - Calibrate before any run: write the known-good game and mutants (effort medium to large, no E2E credits), and require good to pass and every mutant to fail the right check.
   - The result must report hosted behaviour as open, because the platform card says local tests do not establish web-app identity, OAuth scopes or deployment.
   - Cost: plausibly the same order as today's Node run ($5 to $10 on one session), but no GAS run exists on the current card, so this is an estimate.
   - Tension to decide: the prompt cannot name Code.gs functions without going against rubric S01's view that server-held state is overbuilt, so the checks must go through the HTML client.
2. **Audit harness `battleship-create` with real deployment on Grok.** Not cheap and a different game. It needs everything under "missing" above. Run it only once per authorization.

What needs your authorization:
- Any model-backed run: credits.
- Deployment through the MCP to a named Google account, staged then promoted, with an access mode; OAuth consent; Grok credits (no spend cap); cleanup of the created project (the 2026-09-18 attempt created one; whether it was removed is unknown).
- A host-class change that would hand an unattended run the MCP.
- Which harness owns the case, single-player or hot-seat, and whether the prompt requires deployment.

---

## 7. Action list in waves

**Wave 1: now (no credits)**

| # | Action | Effort | Who | Depends on |
|---|---|---|---|---|
| 1 | Destructive-path and oracle-gap tests, each mutation-proven: release dirty tree, install.sh name guard, release-push ancestry, `freeze_package` direct test, release-boundary case A11, stderr-summary test (section 3 rows 3 to 7, 10). | S each | this session | none |
| 2 | `SHIPLOOP_COMMAND` parity test (red today) and the progress soft-failure test (test-only; assertions untouched). | S | this session | none |
| 3 | O4: print seconds on the OK line; with approval, download the run 37391042290 receipts to fill `_DURATION_SECONDS` from GitHub. | S | this session; owner approves the download | none |
| 4 | Selection rules: prompt-marketplace-contract rule, literal-transport id, O11 must-select row; O10 as the audit wrote it. | S | this session | row 3 for durations |
| 5 | Tell the E2E and Run Review session that the 08:23 Battleship run was the Node case, and which Battleship you meant. | S | owner | none |

**Wave 2: next (no credits)**

| # | Action | Effort | Who | Depends on |
|---|---|---|---|---|
| 6 | `mutate.py` unit tests, then O6 with the solo baseline; compare killed sets on all 38 mutants. | M | this session | owner go |
| 7 | O5 memo variant, after the direct `freeze_package` test (row 1). | S to M | this session | row 1 |
| 8 | Battleship `CheckOracleTest`; write the known-good GAS Battleship, mutants and offline checks (section 6, option 1), without running the case. | M to L | E2E and Run Review session | owner picks the harness and game variant |
| 9 | `GIT_CONFIG_*` isolation and `SHIPLOOP_PROGRESS=off` in shared support. | S | this session | none |
| 10 | Before the default flip: planning_review none combinations and the Run Review none-run case (rows 11, 12), `agents/backchain.md` and installed-skill-invocation rows, ask-agent routing after measuring. | S to M each | this session | none |

**Wave 3: later, owner decisions and live runs**

| # | Action | Effort | Who | Depends on |
|---|---|---|---|---|
| 11 | One live GAS Battleship run on Claude Sonnet 5.5. **[CREDITS]** | M | owner authorizes, E2E session runs | row 8 passes its calibration |
| 12 | Hosted deployment variant through the audit harness. **[CREDITS]**, plus deployment, OAuth and cleanup authorization. | L | owner | row 11 |
| 13 | Live runs for the uncovered clauses: a13 person-only route, `--planning-review none`, retention on the current release. **[CREDITS]** | M each | owner, E2E session | none |
| 14 | Decide: rubric suites v2 and v3, external `current_dispatcher` qualification, cursor-imports, marketplace-lifecycle-smoke `--self-test` (not run anywhere), dual-body-guard (fail-first test first), ask-agent-managed-harness. | S | owner | none |
| 15 | At the planning_review default flip: consolidate navigator-contract scans, the shared stage list and `PROTOCOL_VERSION`. At the corpus move: trim `FastPlanningRecordTest` to its obligations. | M | this session | owner go (DNT suites) |
| 16 | Optional: mutants in its own CI job. | S | this session | row 6 measured |

---

## Where the inputs disagree or returned nothing

- **Resolved:** baseline rows (16 committed at both commits; the 17th is uncommitted); the 1.22.0 Battleship wall (at least 17.5 min of stage time).
- **Worktree HEAD moved** from 219c1de6 to 81e0502f while the measuring agent ran. The first about 9 suites ran on the old commit; the rest ran on the newer files.
- **chain-planning-context:** local 147.4 s (near the 120 s ceiling), but 81.1 s on GitHub, so quick eligibility holds on the GitHub figure.
- **Pins in red CI:** the audit said 22 of 36 red runs were pins; none in the last 98 runs. Both are true for their windows.
- **Count-pin churn:** 4 bump commits since 09-28 against 38 commits touching those lines since 09-22. Different windows.
- **cursor-imports:** one review says leave it opt-in (no CI cost), another says remove it. Your call.
- **dual-body-guard:** contested as in section 2; the fail-first test settles only the external half.
- **FastPlanningRecordTest:** one review called its `gate_experiment` rerun a duplicate of improve-runtime. I checked: improve-runtime covers the gate's semantics, but only `test/shiploop-e2e.test.py` reruns `gate_experiment.py`, and the class is in a DNT suite, so it stays.
- **O6 savings:** audit estimate (about 180 s) and my arithmetic (about 350 to 385 s) are unreconciled.
- **Never measured:** GitHub per-suite seconds for node and bash suites and for 37 core suites, apparatus per-module seconds, local quick and release wall time, the cause of the apparatus job's 10.7 to 18.0 min range, the cause of the #471 flake, account-level billing, whether the deployment MCP is available here, and any Apps Script Battleship duration or cost.

---

## Decisions needed from the owner

1. **Which Battleship, and where does the case live.** Options: (A) one offline-checked, single-player, no-deployment `battleship-gas` case in the main harness `cases.json`; (B) the audit harness `battleship-create` (hot-seat, hosted via MCP, Grok only); (C) both. **Recommend A.** It matches the documented open experiment, S01 and the main ladder, and costs no deployment or Grok credits.
2. **Whether to run it, and when.** Options: authorize one live run now; authorize it only after the known-good game and mutants pass calibration; hold. **Recommend the second:** one run on Claude Sonnet 5.5, estimated $5 to $10 (unmeasured for GAS), reporting hosted behaviour as open. Spend nothing before the checks distinguish good from mutants.
3. **Hosted deployment.** Options: require deployment in the prompt; leave it out. **Recommend leave it out** for now; authorize the MCP, Google account, OAuth, access mode and cleanup separately later, if you want the hosted variant.
4. **Release tier (O5 and O6).** Options: do both after O4; do O5 only; hold. **Recommend both, in the audit's order,** O5 as the memo variant and O6 with the solo baseline and the 38-mutant killed-set comparison. O6 needs your go because it changes what the gate runs.
5. **Receipts download (O4).** Options: approve downloading the `hermetic-<group>` artifacts of run 37391042290 (GitHub Actions, about 89 KB total, expire 2027-01-03); fill `_DURATION_SECONDS` from log lines only (node and bash suites stay unknown). **Recommend approve.**
6. **Old-version tests.** Options: keep all; rewrite the 16 baseline rows to carry `planning_review` and then remove the shim and its tests together. **Recommend keep all.** None is confirmed deletable.
7. **ask-agent-managed-harness (39 s on GitHub, no other consumer, unchanged since 09-24).** Options: retire; run full-tier only; leave. **Recommend leave** until O4 shows its GitHub cost against a pole.
8. **Hub set and ask-agent routing.** Options: add native-pilot to `_HUB_SUITE_IDS` (up to about 56 s on hub edits); the fuller derived version; neither. **Recommend native-pilot only,** which is the audit's O11 minimal and closes the 09-24 miss.
9. **rubric-eval suites v2 and v3, cursor-imports, marketplace-lifecycle-smoke `--self-test`.** Options: retire, keep, or run. **Recommend decide v2 and v3 first** (it scopes the rubric-eval tests), and leave cursor-imports opt-in.
10. **Tell the E2E and Run Review session** that the 08:23 run was the Node case. **Recommend yes,** with your answer to item 1.
