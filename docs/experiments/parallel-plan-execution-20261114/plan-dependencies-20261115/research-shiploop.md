R=/Users/dadleet/src/skill-craft; SL=R/skills/shiploop; IP=R/skills/in-parallel; PD=R/skills/plan-dispatcher; AA=R/skills/ask-agent; SPEC=R/test/shiploop_e2e/SPEC.md; J=R/docs/shiploop-parallel-execution-journal.md; D=R/docs/shiploop-review-after-tests-design-2026-10-27.md; ST=R/docs/experiments/parallel-plan-execution-20261114/README.md; FF=R/docs/shiploop-fix-forward-design-2026-11-12.md. `mod.sym` means SL/scripts/shiploop_mod.py symbol sym (IP/scripts/mod.py for harness, harness_paths, delivery); `nav` is shiploop_navigator.py. Unmarked claims are read; [inference] marks mine.

1. Plan and steps
- `plan` writes `work_items` {id,title,follows?,context?} (`nav._normalise_work_items`); `primary.check_queue` requires every primary R-n in some `follows`. Items have no `deps` or `paths`; the queue is visited serially (SL/references/navigator.md, "Recover one existing run"; commit 6116b91ee95143e8d8b387e8be84df338289c053). Backchain's `parallel_groups` is barred from results (SL/references/backchain-planning.md, "Owner binding").
- `step-plan` writes `steps` [{id,task,deps,criteria,proof,paths?,skills,done?}] plus item `paths`, `criteria`, `test_commands`, `expectations` (`nav._normalise_steps`; `prompts`, step-plan duties 4 and 7).
- Validation: `_normalise_steps` (`deps` unique, earlier IDs only; omitted means unknown, not independent), then `nav._evaluate` gates `_check_step_sizing` (proof and criteria required; step `paths` inside item `paths`; no test-only step), `item_scope.proof_order_refusal` (reads step `paths`), `expectations.check_step_plan`.
- Use: `deps` feeds progress/trace views and `step_block`'s "Depends on:" line, never navigation. Steps issue in list order; the cursor is a count (`planning_revision.built_steps`, `nav.step_view`). Commits use item `paths` (`item_scope.commit_scope`); `step_block` says "No path fence". The `_normalise_steps` docstring "nothing reads it" is stale (commit 2a6514d6219a60bea080b4114f3e3433eec0f774).

2. Step lifecycle
- implement (Proof at done) -> test (base RED, candidate, mutation, lint) -> document + Improve review -> ShipLoop's commit stage (`nav._commit_stage`) -> next step. On `delegation: ask-agent` an implement worker shares the checkout, commits nothing, runs no callback (SL/SKILL.md, "Durable handoff").
- Records (SL/references/state-files.md): `state.md` (`accepted`, `history`, one `{stage,action}` per item in `inner_loops`); `results/`; `loops/`; `tests/`; `lint/items/<item>.md` (one base, recaptured per step by `nav._iteration_base`); `iterations/<item>.json` (`number, base, commit, pending` per step); `commits/<implement action>.txt`; `improve/`. Code, `docs/shiploop/` and the Improve receipt live in the worktree.
- Guarantee: a step advances only after its one `feat(<item>/<step>)` commit lands on the iteration's base, holding the gated tree; state, ledger and commit file save in one journaled transaction; `iteration.commit_decision` refuses any other HEAD. Not guaranteed: a clean tree (undeclared files stay uncommitted until `plan-return`, in worktree runs). "Clean-checkout identity" is retired-chain vocabulary (`target_identity`, D 9.1 2c) [inference: live analogues are `iteration.Iteration` and `workspace._fast_forward_ok`].

3. Workspace
- `workspace start` makes `<parent>/.shiploop-runs/<repo>-<stamp>/{workspace.md,worktree/,run/,return-plan.md,return-receipt.md}` and branch `shiploop/run-<sha256(root)[:16]>` from source HEAD or a private snapshot commit (`workspace.prepare`); direct `init` has none.
- All steps commit on that branch; no per-item merge. Return only at `release`/`handoff` (`protocol`): `plan-return` commits leftovers, `review-return` decides paths, `return` is fast-forward, working-tree patch or no-change, with receipt, drift refusal and follow-ups (SL/references/workspace-lifecycle.md). After a return, `release-verify` runs in a clean `consumer-check` copy. Nothing is cleaned automatically (`workspace.leftovers`). Run `.lock` and `.workspace.lock` serialize writers. The Improve child shares the checkout, one writer (SL/references/improve-context.md).

4. In Parallel and Plan Dispatcher
- IP: one coordinator; tasks {id,objective,expected_result,write_set}, glob-free, non-overlapping (`harness.normalized_request`, `harness_paths.scopes_overlap`); workspace current|worktree; mode edit|report-only|ephemeral; integration apply|return-only; combined `checks` required for edit+apply; `capacity` default min(5,tasks), 1 for current-workspace edit.
- Barrier: `harness.finish` needs Dispatcher `complete`, then one `delivery.deliver`: same baseline, per-worker verify-return, base/path/overlap checks, one `git apply --check` then apply, HEAD and index untouched, no commit; then checks that must not change the source. Return-only keeps patches/commits. "An unknown or still-running launch is never retryable" (IP/references/contract.md).
- Excluded: dependent graphs (contract.md; `deps: []` in `harness.initialize`); adopting ShipLoop or Dispatcher runs (IP/SKILL.md).
- PD: frozen dependency graphs, `capacity`, `complete` = all accepted (PD/scripts/state.js), no wave barrier, rejection blocks descendants, replan = new run, integration is the parent's merge-and-verify step; a worker lost with its session retries with `native_status: "unavailable"` (PD/references/protocol.md).
- AA: current workspace has one in-place writer, no commits (AA/references/current-workspace.md); consumer-owned route one writer in the bound candidate; helper-managed worktrees return commits or patches (AA/references/git-integration.md).

5. Retired chain
- Retired by ad30aa1c82665435c1e69771ef079d80d7b92079 (7,710 lines) on the owner's G1, 2026-10-29, "Adopt (a2)" (D 9.2; fb4b284368ffb8c0d32d175915e299849ed8a8b8). Reason (8eca9d64826e0073540b6029b6071fc91b553e8e): it broke four rules of the per-step iteration (`done` fast-forwarded worker commits the commit stage refuses; `_per_step_expected_target`; clean-checkout `target_identity`; a binding inside one implement action); its speed gain was never measured; it bought isolation and unattended lost-worker retry, accepted as cost.

6. Invariants and owner rules
- Build, test, document, review, commit each step before the next (owner 2026-10-27, D 8; SL/references/navigator.md, "Step commits").
- Only the commit stage commits; one mechanism per job (SPEC S-5, S-12; `iteration`).
- Scripts own graph and state; one owner, one callback; workers never advance it (S-1, S-2; `reference.OWNER_TEXT`).
- Fix forward: done steps never rerun (FF, "The rule").
- Proof uses only this step and earlier accepted ones; floors cumulative (`nav._check_step_sizing`; SL/references/testing-and-documentation.md, "Floors").
- Packets stand alone; no clear pause (S-6; navigator.md, "Context boundaries").
- Unattended (S-14); no loop caps, ask before any limit (S-10; R/AGENTS.md, "Decisions") [inference: a capacity counts].
- Script-run check is evidence (S-9); one candidate writer (a scheduling rule, not a lock); lost worker shown stopped before replacement (SL/references/improve-context.md; D G1).
- One supported version; no backgrounded workflow (SL/SKILL.md, "Saved runs the current code cannot load", "Start or resume"); visible host-tool commands; quality, then tokens, then time; material difference only (ST, "What the repository already says"; memory notes unopened).
- Ask first for behaviour trade-offs; `changes/shiploop/` note, E2E round before release, no squash (R/AGENTS.md). Concurrency must not change a verdict (SPEC, "Parallel work", E2E runs).

7. New script-owned state [inference, from the cited precedents]
- Barrier: none now (one action per item; prefix rule in `iteration.start`). Needs per-step status and an all-accepted gate under the run lock (PD `complete`, IP `finish`).
- Merge order: plan order fits `iteration.start`; completion order is J E13's. Needs a per-merge pending record through the commit stage (IP apply does not commit).
- Conflict: step `paths` optional and globbed; need mandatory disjoint paths, an out-of-scope check, per-step bases (one `lint/items/<item>.md` now; the ledger keys base per step) and abort-and-retry (J F41: about one task round).
- Re-verification: Proof, RED, GREEN, mutation assume a linear base (D 9.1 2c option b); rerun on the merged tree (J F44).
- Partial failure: sibling and dependent disposition, late returns refused, proof of stop.
- Cleanup: ShipLoop never deletes; IP closes integrated worktrees (`harness.finish`); /Users/dadleet/src/AGENTS.md allows removing only incorporated or preserved worktrees; needs an owner decision and a ledger.
