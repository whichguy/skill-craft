Found **four material defects**: one P1 and three P2s. I read the three full commit messages, design, diff, and relevant earlier decisions. Verification below used read-only code tracing and in-memory Python; I did not run the full CLI/E2E suite.

1. **P1 — Improve import bypasses both new fix-forward gates.**  
   [shiploop_navigator.py — `dispatch`, Improve import](/Users/dadleet/src/skill-craft/.claude/worktrees/fix-forward-5308ed/skills/shiploop/scripts/shiploop_navigator.py:10194)

   `_check_fix_forward` runs in `_evaluate`, but the separate Improve-import validation sequence omits it. Import then calls `finish_improve`, whose canonicalization validates shapes without enforcing these invariants.

   **Failing history:** S1 completes; S2 sends back; the producer submits a valid amendment marking S1 done. Improve returns a `final_result` that removes S1’s mark and changes its task. Import accepts it, and `_StepLists.plan` clears the retained actions because the plan has no marks. Execution resumes at S1. The same omission permits Improve to change a frozen case’s oracle.

   **Verification:** Built a valid, unpersisted `delegation="ask-agent"` state through the pure navigator API. The valid seed passed `_fix_forward_refusal`; the altered final result produced the expected refusal when checked explicitly. Nevertheless, `finish_improve` accepted it. The resulting cursor reported:
   ```text
   import accepted changed task= REOPEN FIRST STEP
   resumed cursor= S1 built= 0
   ```
   I traced `dispatch` through its import validators to confirm no intervening fix-forward check exists.

   **Fix:** Check the effective final result with `_check_fix_forward` before accepting the Improve import, covering both step-plan and test-spec.

2. **P2 — Omitting `test_cases` can silently drop frozen cases.**  
   [shiploop_navigator.py — `_frozen_case_refusal`](/Users/dadleet/src/skill-craft/.claude/worktrees/fix-forward-5308ed/skills/shiploop/scripts/shiploop_navigator.py:3071)

   The gate calls `normalise_test_cases(result.get("test_cases"))`. An omitted field supplies `None`, raises `ExpectationError`, and returns without checking frozen cases. Its comment assumes another gate will refuse the shape, but omission is legal when no focused IDs remain.

   **Failing input:** S1 owns C1/TC-1 and completes. An amendment preserves S1 and C1 exactly, but replaces the focused command with a check command confirming C1. No focused IDs remain. The subsequent test-spec omits `test_cases` and supplies `assumptions: []`. TC-1 disappears from the specification.

   **Verification:** The amendment passed `_fix_forward_refusal`, `_check_submitted_test_commands`, and `_check_submitted_layers`. For the new specification:
   ```text
   omitted cases freeze gate= None
   handoff gate= None
   ```
   `_canonical_result` also accepted it. Submitting the equivalent explicit `test_cases: []` correctly refused removal of TC-1.

   **Fix:** Treat an absent case list as empty for the frozen-case comparison, while retaining the ordinary shape handling for malformed supplied lists.

3. **P2 — Retained steps lose their cumulative test-count floors after amendment.**  
   [shiploop_test_loop.py — `accepted_counts`](/Users/dadleet/src/skill-craft/.claude/worktrees/fix-forward-5308ed/skills/shiploop/scripts/shiploop_test_loop.py:1080)

   This reader still starts strictly after the newest step-plan action. Consequently, it excludes all retained done-step test records. Both `accepted_counts` and its `earlier_steps=True` variant return empty at the first resumed step, disabling the additive floor in `floor_detail`.

   **Failing history:** S1’s focused command runs 50 tests. S2 sends back, then resumes under a valid marked amendment with one new case, TC-2. S2 can replace an unnamed earlier test with TC-2 and keep the total at 50, while still printing both required IDs. The intended earlier-count-plus-new-ID floor is 51.

   **Verification:** Supplied in-memory history and mocked record reads containing S1’s accepted count of 50 and a base count of 50. The projection correctly retained S1’s test action and identified only TC-2 as new, but:
   ```text
   after amendment: accepted={} carried={} floor=50
   without amendment: accepted={command:50} carried={command:50} floor=51
   ```
   This also contradicts the explicit cumulative-floor protection recorded in commit `b55909179b89bfc63bba67d4cdbb833c700df147`.

   **Fix:** Derive accepted counts from the retained per-step actions, excluding the interrupted attempt and preserving genuine resets for unmarked plans.

4. **P2 — A done step without criteria prevents later steps from gaining criteria.**  
   [shiploop_navigator.py — `_check_step_sizing`](/Users/dadleet/src/skill-craft/.claude/worktrees/fix-forward-5308ed/skills/shiploop/scripts/shiploop_navigator.py:3121)

   Whenever the amended plan defines any criteria, sizing requires every step to have a nonempty criteria list—including frozen done steps that validly had none.

   **Failing input:** The original documentation plan has S1/S2, each with `criteria: []`, a proof, and no top-level criteria. S1 completes. After S2 sends back, the amendment preserves marked S1 exactly and introduces C2 and its check solely for unfinished S2.

   The amendment cannot satisfy both gates: leaving S1 unchanged fails sizing; adding C2 to S1 violates the frozen-row comparison.

   **Verification:** The original plan passed `_check_submitted_test_commands`. The amendment passed `_fix_forward_refusal`, then failed sizing with:
   ```text
   step S1 must list criteria: the IDs of the criteria it satisfies (C2).
   ```

   **Fix:** Preserve the validity of retained done rows when applying sizing requirements to newly planned work.

I verified no separate cursor or commit-attribution defect. I also found no material defect in `REPEAT_LINE` or the requested focused-command pipeline cases: runner output piped through `grep`, `cd`-prefixed runners, and a runner followed by `rg` all classified as `search_only=False` and passed the new refusal. A `cd` followed solely by `rg` correctly classified as a search.