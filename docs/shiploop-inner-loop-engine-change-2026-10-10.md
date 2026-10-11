# ShipLoop inner loop, engine change: 17 → 8 stages (2026-10-10)

Status: **in progress** (phase A). The owner decisions are in
`docs/shiploop-inner-loop-stage-diagnosis-2026-10-10.md` ("Revision: 8 stages") and in the accepted
recommendations below.

Sources for the new prompts:
- `docs/experiments/inner-loop-redesign-20261010/drafts.json`: the merged, reviewed drafts per stage. Each has a
  prompt, a contract, gate_after and notes.
- `docs/experiments/inner-loop-redesign-20261010/coverage-*.json`: 389 obligations, each with its status and fix.

## The graph

`shiploop_stage_spec.py` is done. INNER is: step-plan, test-spec, validate-existing, implement, test, document,
verify, carry-forward. There are 24 stages in total.
- Every inner row has the entry run `loop-contract` and the complete run `loop-terminal`.
- implement has `improve="step"`.
- `repeat` is dropped from every inner stage.
- The revise range runs from test-spec to verify.
- `ITEM_COMMIT_STAGES` is now (document, verify).

New entry/complete runs:
- `expectation-check`: at validate-existing entry and complete.
- `test-base`: at test.
- `test-loop`: at test.

Removed runs: test-probe, test-red, quality-terminal, quality-contract, test-loop-contract and report-lint.

## Accepted owner decisions (2026-10-10)

1. The model may invoke /until-loop.
   - The card gets `disable-model-invocation: false` and a first section that starts from a parent-written
     contract file unchanged.
   - The vendored copy is `skills/improve/runtime/until-loop/`. The separate until-loop plugin repo follows in its
     own release.
2. The test-count floor is the larger of the base run's regression count and the most an earlier run of this
   action counted. A deliberate retirement is declared in `retired_tests: [{"id", "reason"}]`.
3. `red_na` is a list of test IDs, each with a reason: `red_na: [{"id", "reason"}]`. On the base checkout, a new
   test that fails because a file this item adds is missing counts as RED.
4. The lint gate runs on every implement step, not only the last.
5. `planning_review: none` does not skip the per-step Improve.
6. implement keeps its own loop, and an Improve child follows each step.
7. document is issued only when `item_scope.behavioural(changed paths)` says so (script rule).
8. No verify rerun skip: verify always reruns.
9. carry-forward has a skill decision: `skill: {decision: none|reuse|update|create, ...}`. A created or updated skill
   gets a script commit of its directory and index.
10. `complete --check-only` runs the stage's script gates without completing.
11. ShipLoop refuses a test-spec case ID that no focused command lists.

## Module ownership and interfaces

Each module has one owner. The owner edits only its files and reports any navigator hook it needs, with its exact
signature. The navigator (`shiploop_navigator.py`), `shiploop_protocol.py` and the CLI belong to the main session.

### `shiploop_loops.py` (new) and `shiploop_quality.py`: the Until Loop for every inner stage
- `STAGES = stage_spec.INNER`. The contract text per stage comes from the reviewed drafts' contracts. `work`,
  `exit_condition` and `repeat_condition` are constants here. The exit condition is the same text as the row's
  done_when, joined and numbered.
- `required_trivial_reviews` is 1 for verify, otherwise 0.
- `contract(root, state, action_id) -> dict` is rebuilt deterministically from state, in the runtime's exact schema.
  `context.request` is a locator (`<run>/state.md`), never the request text.
- `contract_writes(root, state) -> dict[str, str]` gives the run-relative path → text for
  `loops/<action>-contract.json`. It is called on entry to every inner action.
- `receipt_path(root, action_id) -> Path` is `loops/<action>-terminal.json`.
- `invoke_lines(root, state) -> list[str]` renders the strong block for the packet:
  - "INVOKE /until-loop NOW with the argument below, verbatim. Do this stage's work only inside that loop.";
  - the argument: Work, then "Exit when ALL of these hold" with the numbered conditions, then "Repeat while", the
    contract and the receipt;
  - "How to invoke": the Skill tool `until-loop` on Claude Code, or the card path;
  - the exact start command;
  - "Never write or edit the receipt. If it exists and is active, run its next_argv instead of starting again."
- `check_terminal(root, state, result) -> None` raises `LoopError` with the refusal text. It reads the receipt named
  in `evidence_refs`, rebuilds the contract from state and compares them. It requires `exit_assessment` satisfied;
  when `required_trivial_reviews` is 0, a non-trivial final report is accepted. Refused: `repeat`, a missing
  receipt, an active receipt, or a mismatched contract.
- quality keeps the code-craft rubric file and the change inventory, now for verify. `QUALITY_*` constants are
  replaced by verify's contract texts in the loops table.

### `shiploop_test_loop.py`: the test stage and verify's rerun
- `STAGES = ("test",)`. Remove PROBE_STAGE, RED_STAGE, the REFINE floor reset, the test-green/regression split
  and `baseline_lines`.
- `RERUN_STAGES` stays (verify, system-test, release-verify), and `verify(...)` stays.
- `base_check(root, state, work_item, action_id) -> list[str]` raises `TestLoopError`. It runs every focused and
  regression command in a temporary detached worktree at the item's lint base, with only this item's test files
  copied in.
  - Refused: a new test ID passes there, unless `red_na` lists it. An import or load failure caused by a file the
    item adds counts as failing.
  - It records the base regression count.
  - It needs a per-test-ID pass/fail reader built from the runners' listing output.
- `loop_run(root, state, work_item, action_id) -> list[str]` raises `TestLoopError`. It runs every recorded command
  on the candidate and refuses unless each exits 0, every listed ID ran, and the count is at least the floor
  (`max(base count, ratchet)`, less any `retired_tests`).
- `loop_lines(...)` lists the commands for the test packet. The 11-refused-runs cap and the timeout and start-failure
  rules are unchanged; refused base runs count toward the cap.
- `red_na` and `retired_tests` are result fields of the test stage, validated here.

### `shiploop_expectations.py` (new) and `shiploop_item_scope.py`
- `check_step_plan(result) -> None` raises `ExpectationError`, run at the step-plan gate. It checks:
  - `expectations: [{id, state: works|absent|broken, statement, steps, check, from?}]`;
  - each check is one read-only shell command;
  - every existing step path has a works or broken expectation, and every new path an absent one;
  - every open plan assumption whose consumer is this item appears with `from`;
  - `test_commands` has a check row or `check_na`;
  - each step's `skills: [{name, why, locator?}]` has a locator that exists;
  - every test-spec ID check belongs to test-spec's gate: `check_test_spec_ids(root, state)`.
- `run(repo, expectations, run_dir, action_id, timeout) -> list[dict]` returns, per check, its id, state, exit, a
  summary, the output path and whether it matches its state. It runs in the execution checkout, which nothing has
  changed yet.
- `entry(root, state) -> tuple[dict[str, str], bool]` returns the record writes and whether all expectations match.
  When all match, the navigator records validate-existing as done by script and issues no packet.
- `check_complete(root, state, result) -> None` reruns the checks and refuses a mismatch. A `revise` result must carry
  `failed_expectations: [{id, actual, route}]`.
- `check_preparatory_commits(repo, base, expectations) -> None` checks that each commit since the lint base touches
  only the paths of a mismatched works expectation.
- item_scope:
  - add `behavioural(paths) -> bool` (document issuance);
  - `TEST_STAGES = ("test",)`;
  - remove the skill-stage N/A machinery (SKILL_NA_*, skill_surface*, no_skill_item, skill_scope_refusal);
  - `left_out` becomes test when the item has no test commands, and document when not behavioural.

### `shiploop_prompts.py`: duties, references and Improve scopes for the 8 stages
- `DUTIES`, `STAGE_REFERENCES`, the per-stage scope summaries, `IMPROVE_*` and COMMON's Improve list are rewritten
  from `drafts.json` and the coverage fixes.
- The new `IMPLEMENT_STEP_REVIEW_FOCUS` carries CODE_CRAFT verbatim.
- STEP_SIZING says the test stage writes tests after implement.
- The dynamic parts are rendered by the navigator, so DUTIES refers to them by name:
  - the until-loop block (`loops.invoke_lines`);
  - the step lines and the step's skills;
  - the test command list (`test_loop.loop_lines`);
  - the expectation results.

### Consumers
- `skills/shiploop-run-review/scripts/export.py`, `defaults/stages.json`.
- `shiploop_planning_context.py`, `shiploop_navigator_dry_run.py`, `shiploop_progress_data.py`,
  `shiploop_context_index.py`, `shiploop_reference.py`.
- The E2E harness stage lists: `test/shiploop_e2e/*.py`.

### Navigator, protocol and CLI (main session)
- `STATE_VERSION` 5.
- The validate-existing auto-skip.
- The step Improve rule.
- The lint gate on every implement step.
- The item commit at verify and the skill commit at carry-forward.
- `complete --check-only`.
- `_begin_inner_loop` and the inner-loop entry hooks.
- `static_entries` counts verify entries.

## Journal
- 2026-10-10: stage table changed (24 stages); lint's advisory entry moved to verify; INNER_GROUPS became the five
  phases.
- 2026-10-10: five module workers landed:
  - shiploop_loops (contracts for all 8 stages, tested against the real runtime);
  - the test stage (base run, candidate run, per-ID reader, red-check);
  - shiploop_expectations and item_scope;
  - prompts (151 of 178 coverage fixes; the other 27 are engine work);
  - consumers.

  The navigator is wired. `graph-dry-run --scenario all` passes all 7 scenarios on the inline and ask-agent routes.
- 2026-10-10: the first full suite run on the engine change failed about 500 tests across 27 of 80 suites.
  - The largest cause, about 270 tests, is CLI fixtures completing an inner stage without a loop receipt.
  - The next is tests naming removed stages.
- 2026-10-10: until-loop 0.8.0 prepared in /Users/dadleet/src/until-loop, branch feat/parent-written-contract (local;
  not pushed). It sets disable-model-invocation false and adds "Start from a parent-written contract". The shell test
  pins the new policy. 42 unit tests, 11 shell checks and `claude plugin validate` pass.

## Learnings, and the improvements they led to (2026-10-10)

| # | Learning | Improvement | Status |
|---|---|---|---|
| L1 | Every inner `complete` now needs a loop receipt, so every CLI fixture must run a loop | `test/shiploop_loop_support.finish_loop`: the real runtime, from ShipLoop's own contract; never a hand-written receipt | done; smoke-tested at step-plan |
| L2 | Removing `listing_problem` lost step-plan's refusal of a command list too big for the loop contract | I2: refuse at step-plan, using the loops module's budget | in progress |
| L3 | After a revise that follows implement, absent expectations fail on the item's own new files | I3: on re-entry, run the checks in a worktree at the item base | in progress |
| L4 | `--check-only` ran real gates: lint auto-fix, counted test runs | I4: report-only lint, `red_check`, a non-counting candidate run, no commit | in progress |
| L5 | `QUALITY_*`, `PASS_OR_STOP` and the old loop texts lost their consumers | I5: remove them | in progress |
| L6 | The dry run used a fake Improve card, so its packets never showed the INVOKE block | I6: the dry run uses the bundled card | in progress |
| L7 | A preparatory fix committed by the model would break ShipLoop's rule that the model commits nothing | ShipLoop commits it on accept; the gate checks only its paths | done |
| L8 | The test stage's base must include the preparatory commit, or a fixed behaviour looks red for the wrong reason | `base_commit` is the preparatory commit when one exists | done |

- 2026-10-10: merged to main at 8932b849, then e4777c78 (emit writes a missing loop contract) and 13d278dd
  (shiploop-e2e-audit oracle; main's CI quick job had gone red because that family is outside the ShipLoop suite list).
  - Lesson: run `bash test/run-all.sh --group quick` before pushing a stage-table change.
- 2026-10-10: four live step slices on 13d278dd all pass, with validate-existing recorded by script in every case.
  They are 2-38% slower and use 9-24 more turns than the 17-stage slices. Details: test/shiploop_e2e/LEARNINGS.md and
  evidence/step-slices-8stage-2026-10-10.json.
- Open:
  - a `recorded_by: "script"` marker on script-recorded history rows (harnesses match summary text today);
  - the Skill-tool route for /until-loop needs the until-loop plugin;
  - the cost of loop ceremony on one-pass stages;
  - the four-part packet re-cut (packets still 400k characters per item offline);
  - the B1/B2 probe fixes;
  - Run Review's v4 history handling (the fork, branch rr8-2ce5e7).
