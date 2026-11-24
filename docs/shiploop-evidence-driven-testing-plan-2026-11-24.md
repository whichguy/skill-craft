# Evidence-Driven Test Planning, Execution, and Fix-Forward Replan (2026-11-24)

## Goal

Make ShipLoop's test planning and test execution evidence-driven and progressively revealing without sacrificing upfront forecasting or pre-code test specifications:

1. **Sequence 1 — Open `test`'s structured evidence channel:**
   - Give `test` read access to `architecture.md` (`STAGE_FILES["test"] = ("environment.md", "architecture.md")`) so it understands module boundaries and invariants.
   - Surface the implementation's actual product-code diff (`CHANGED_SINCE_BASE` + full patch written to `RUN/fields/<action>-product-diff.patch`) on `test`'s packet and loop contract so tests target concrete branches/operators rather than guessing.
   - Allow `test` to record `added_tests` (`registered()` includes `test`), optional `test_findings` (`[{id, finding, evidence, impact: "none"|"local"|"amend-remaining"|"system-test", next_step}]`), and optional `assumptions` open items (adding `"test"` to `OPEN_ITEM_STAGES`, `REFLECT_AND_REVISE_PRODUCERS`, `PER_STEP_STAGES`, and `OPTIONAL_OPEN_ITEM_STAGES`).
   - Forward `not-exercisable` `mutant_dispositions` from `test` (alongside `test_findings`) to `system-test-author` / `system-test`, as well as `test_findings` to `document`, `step-plan` (on `replan_remaining`), and `reflect-and-revise`.

2. **Sequence 2 — Upgrade `test`'s Until Loop & post-edit Proof gate:**
   - Rewrite `WORK["test"]`, `REPEAT["test"]`, and compact `DUTIES["test"]` into a 2-beat evidence-reveal + 4-tier triage loop (local fix -> document-handoff -> amend-remaining via `document` / `step-plan` -> outer-test gap via `test_findings`/`assumptions`, using `RUN/experiments/` for diagnostic probes when behavior is ambiguous).
   - Snapshot `entry` tree on `test` entry; when `test` edits product code while fixing a revealed defect, re-run `step_proof` at `test` `done`.

3. **Sequence 3 — Commit-then-amend fix-forward (`replan_remaining` on `document`):**
   - Allow non-final `document` `done` to emit optional `replan_remaining: {"reason": "...", "affects": [...]}`.
   - ShipLoop commits `S1..Sk` normally (`_commit_stage`), recaptures the item base (`_iteration_base`), marks `S1..Sk` `"done": true` in `_StepLists`, clears downstream per-step queues, and routes to `step-plan` (incrementing `revisions[item]`, preserving `Sk` committed work) so `S(k+1)..Sn` are re-sequenced and re-specified from empirical evidence.

4. **Sequence 4 — Sync test planning with vertical slicing & experiments:**
   - Add `"test-strategy"` to `OPEN_ITEM_STAGES` / `OPTIONAL_OPEN_ITEM_STAGES` with `due_stage` supporting `"plan"`, `"prepare"`, and outer stages (`_settled()`).
   - Quote `intake` K8/experiment questions at `test-strategy`.
   - Allow `step-plan` to submit optional `targets` alongside `test_layers`, validating and merging them across prior done work items so `stateful_targets()` reflects newly uncovered stateful boundaries.
   - Surface earlier done work items' passing regression commands at `W2+` `step-plan` so cross-slice regressions are carried intentionally.
   - Tighten `DUTIES["test-spec"]` around spec boundary pairs and cohesive `describe('<ID> ...')` multi-test groups instead of monolithic test blocks.

5. **Sequence 5 — Harden outer testing (`system-test-author`, `system-test`, `release-verify`):**
   - Fix `DUTIES["system-test"]` duty 4 and `test_loop.verify()` / `_explain()` so outer stages (`system-test`, `release-verify`) never edit or get told to edit product code or recorded commands directly: product defects route to `add-work`, and wrong/uncountable commands route to `send-back` (`system-test-author` / `release-plan`).
   - Surface `test_findings` and `not-exercisable` mutants at `system-test-author` and `system-test` with explicit outer evidence triage.

## Guardrails

- Keep `test-spec` before `implement` (pre-code oracles).
- Keep `shiploop_mutation.py` operators unchanged.
- Keep `release_commands(..., last_item=True)` intact.
- Keep protocol 4, state v7, 23-stage graph, no loop count caps, and `< 20,000`-char printed packet heads.
- Preserve backward compatibility for fixtures that omit optional `assumptions`, `test_findings`, `replan_remaining`, `added_tests`, or `targets`.
