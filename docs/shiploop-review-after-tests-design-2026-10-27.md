# Improve review after the item's tests pass (design T), 2026-10-27

Status: **design only; nothing built.**

Consumer: first the owner, deciding D1 to D4 (§6), then the session that builds T. It sits beside
[design C](shiploop-measured-width-design-2026-10-27.md), which decides how many implement reviews an item gets. T
decides when they run.

The owner's request, in their words:
- "I think the improved loops themselves are very costly, so I'm thinking more: 1. Author the code. 2. Do the tests.
  3. Make the code fit the tests. 4. Run the improved loop after the test succeeds."
- "We really should be very verbose about the tests step itself. We should run the tests, continue running them and
  improving until the test succeeds, or we modify the tests and then they succeed."

**Evidence.** The five battleship runs that C and B use, all under `~/e2e-runs/`:
- Sonnet: 01b9b3 (per step), 491d9a (item review), 36036c (2.18.0);
- DeepSeek: 978478 (per step), 759a03 (item review).

The tables are in [`docs/experiments/e2e-review-after-tests-20261027/`](experiments/e2e-review-after-tests-20261027/):
- `improve-cost.txt`: each run's Improve minutes by kind of review, made by `improve_cost.py` from the earlier
  `improve-windows.txt` tables;
- `test-stage-fixes.txt`: the product code each item changed after its review, and what each test stage says it
  fixed.

## 1. The order today and proposed

| | today | T |
|---|---|---|
| 1 | implement steps: lint after each edit; lint gate and the step's Proof at done | same |
| 2 | **Improve review** of the item's code, after the last step | the test stage (below) |
| 3 | test stage: write the tests from the test spec, run them, fix the code until they pass; base RED check and mutation check | **Improve review** of the item's code and its tests, which now pass |
| 4 | document | document |
| 5 | verify: reruns every recorded test command | verify, unchanged; it now also checks the review's edits |

So today, when the review runs, the item's tests do not exist yet. The review can check its own edits only with lint
and the step Proofs, and its packet says the test stage will run over it later.

## 2. The test stage already runs the owner's steps 2 and 3

The test stage's packet (in 36036c: `RUN/packets/nav-b54b16d7…md`, 45,540 bytes) works like this:
- **The loop has no limit.** The stage runs inside an Until Loop with no iteration limit.
- **Its work** is duty items 1 to 8, "until every case is a passing test the focused command runs".
- **It exits** only when four things hold:
  - every case in the test spec is a test;
  - no new test passes on the item's base;
  - one complete run after the last edit passed every recorded command;
  - every test changed to get a pass has a recorded independent reason.
- **Duty 4 is the owner's step 3:** "After each change run every recorded command … fix the product. Change a test …
  only for an independent reason written in RUN/notes/<action>.md. Never weaken, delete or skip a test to get green.
  A repeated unchanged failure is not progress: change approach."

**What is not yet verbose is the first line a model reads.** The Goal says only "Write a test per quoted case,
titled with its ID; make every recorded command pass in WORKTREE; fields go in the result." T rewrites the Goal to
state the loop:

> Write the item's tests from the test spec, one per quoted case, titled with its ID. Then run every recorded
> command, fix the product for each failure (change a test only for an independent reason you record), and repeat
> until one run after your last edit passes every command. Fields go in the result.

That is about 300 characters, against 120 now. The packet's printed part has a byte bound, which the build checks;
when a size bound and a needed rule conflict, the bound is raised rather than the rule cut.

## 3. What the runs say

**3.1 The tests catch defects the review missed.** Product code changed after the review in 4 of the 5 runs
(`test-stage-fixes.txt`). Two test stages name the defect they fixed:
- **01b9b3 W1**, after three step reviews: "randomPlacement now enumerates legal positions (previously infinite loop
  for a constant rng)".
- **978478 W2:** "a signal-killed child reports no exitCode, so server.js now closes its socket and exits 0 on
  SIGTERM/SIGINT".

So "make the code fit the tests" finds real defects, and with T it finds them before the review spends passes on that
code.

**3.2 The tests do not catch the review's defect classes.** In 491d9a every test passed, and `GET //`, the
unchecked options and the stale fire reply all shipped. The test spec is written from the spec, which says nothing
about those behaviours, so no case tests them. Running the tests first does not replace the review, and it does not
end the review's loop sooner. That loop stops on its own rule: a pass that changes nothing material.

**3.3 The review's fixes got tests because the review came first.** In 36036c the test stage reports: "Sub-cases cover
the implement stage's not_covered items and the review's crash/500 fixes". The mutation check then covered those
tests. Under T the review comes after the tests, so it has to write the tests for its own fixes (§4, point 4).

**3.4 What the review costs** (`improve-cost.txt`, awake minutes):

| run | Improve, share of run | planning reviews | implement reviews | end-of-work reviews |
|---|---|---|---|---|
| Sonnet 01b9b3 (per step) | 9.4, 25% | 4.9 | 2.7 (3 reviews) | 1.8 |
| Sonnet 491d9a (P0) | 8.8, 28% | 4.0 | 1.6 (1) | 3.2 |
| Sonnet 36036c (2.18.0) | 10.2, 31% | 5.9 | 1.8 (1) | 2.5 |
| DeepSeek 978478 (per step) | 86.3, 39% | 42.1 | 28.1 (12) | 16.1 |
| DeepSeek 759a03 (P0) | 62.7, 38% | 24.8 | 10.4 (3) | 27.5 |

- Improve is a quarter to two fifths of a run.
- Since P0 the implement review is 17 to 18% of Improve. The planning and end-of-work reviews take the other 82 to 83%:
  across the five runs, planning takes 40 to 58% and end-of-work 19 to 44%.
- Moving the implement review saves little by itself. If the aim is to cut Improve's cost, the minutes are in the
  planning and end-of-work reviews. On DeepSeek 759a03, spec and test-strategy took 18.8 minutes and carry-forward
  13.2. That is D4, outside this design.

## 4. The design (T)

1. **Where the review starts.** Rule `item` moves from the implement stage to the test stage (`IMPROVE_RULES`,
   `stage_spec.with_improve("item")`). The review starts when the item's test stage's done is accepted, which means:
   - every recorded command passed;
   - the base RED check held;
   - the mutation check held.

   No review runs after an implement step.
2. **The no-change skip stays** (P4). A test-stage done with no file changed since `item_base`, a reissue after a
   send-back, starts no review.
3. **The review's handoff:**
   - the item's whole change since `item_base`, code and tests: `git -C <repo> diff <item_base> <bound>`;
   - the test stage's result: the tests by ID, their sub-cases, the `not_covered` it left and `red_na`;
   - the recorded commands with their floors;
   - the Accepted step lines.
4. **The review's own test loop** (the owner's step 4, worded as plainly as the test stage):
   - After each edit, run every recorded command.
   - A fix that changes behaviour adds a test for it: a sub-case `<ID> (<letter>)` of the closest case, the form the
     test stage's duty 3 uses.
   - Change an existing test only for an independent reason, recorded in the review's notes. Never weaken, delete or
     skip a test.
   - A pass ends with every recorded command passing.
5. **What checks the review.** Verify's `test-rerun` already reruns every recorded command and refuses done unless
   each passes, so no new gate is needed. The rerun line in the review's handoff becomes "the item's verify stage
   reruns its recorded commands over it". The tests the review adds are not mutation-checked, because the mutation
   check ran in the test stage. §5 watches this.
6. **Order with the other stages.**
   - Document follows the review, so it documents the reviewed code.
   - The ask-agent route builds every step in one implement action, and its review also follows the test stage.
7. **With design C.**
   - The groups are measured over the implement steps, as C says.
   - The point where the reviews wait moves from the item's last step to the test stage's done.
   - Each group's review is still keyed to that group's last implement step (C's D3), with the test stage's result
     parked.

   Without C, the one review is the test action's own Improve stage, which needs no state-model change.

**Where it lands (T without C):**
- `shiploop_stage_spec`: rule `item` on `test`, and its comment; the test row's Goal (§2).
- `shiploop_navigator`:
  - `_improve_checkpoint` (rule `item` at test, with P4 against `item_base`);
  - the handoff builders, `_item_steps`, `_review_base_line` and `_item_review_lines`, for a test-stage child;
  - `_improve_rerun_clause` (verify reruns);
  - B's per-step branches and `_wide_item`, which C replaces in any case.
- The review focus for the item: code and tests, and point 4's test loop.
- The words:
  - the glossary's Improve stage row;
  - the common prompt's "after each work item's last accepted implement step", which becomes "after each work
    item's test stage";
  - `navigator.md` and `improve-stages.md`;
  - the Run Review stage catalog's check text.
- Change notes: shiploop, `bump: minor` (it changes the review schedule); shiploop-run-review, patch.

**Tests.** Fail-first, through the real CLI:
1. A two-step item starts no Improve stage after either implement step. It starts one after the test stage's done:
   its base is `item_base`, and its handoff names the recorded commands and the test result.
2. A test-stage done that changed no file since `item_base` starts none.
3. The review's rerun line names verify.
4. After a review edit that breaks a recorded command, verify refuses done. This is the existing gate, driven through
   the real route.
5. The test packet's Goal reads as §2.
6. Re-pin the packet counts that move (`SMALL_HOME_FINGERPRINTS`, e2e-efficiency), giving the reason.

## 5. How to tell it worked, after the build

| run | must hold | should improve | watch |
|---|---|---|---|
| Sonnet battleship (`--backend anthropic`) | PASS; no send-back to implement | every review commit that changes behaviour adds a test; probes as in `probes.md` | Improve minutes against 9.4, 8.8 and 10.2; whether the page defect is fixed (it needs C's groups, §3.2) |
| DeepSeek battleship | PASS; no send-back to implement | Improve minutes within 10% of 759a03's 62.7 | the review's finding passes on code the tests already fixed |

**The forecast, stated honestly:**
- T alone should not fix the wide-item miss: the stale fire reply is in no test case.
- T's gains are elsewhere:
  - the review runs a real suite;
  - the test code gets reviewed;
  - spec-level failures are fixed before the review.
- Results are n = 1 per model. A regression is rerun before it decides anything.

## 6. Decisions for the owner

- **D1. Build T, and with what.** Recommended: T with C, so one review per measured group runs after the tests. On
  Sonnet only a per-step review has caught the page defect, and no test covers it (§3.2). The extra reviews cost
  about a minute each on Sonnet. The alternative is T alone first, with one review per item, and C only if that
  review still misses.
- **D2. The review's fixes carry tests.** Recommended: a handoff duty (§4, point 4), measured in the live run. The
  alternative is a gate that refuses a review whose commits change code but no test, unless it records why.
- **D3. The test stage's Goal.** Recommended: the spelled-out loop of §2.
- **D4. Improve's cost.** Since P0, 82 to 83% of Improve's minutes are planning and end-of-work reviews (§3.4). Cutting
  them is a separate design, if cost is the aim.

## Not in this design

- Improve's pass loop and its stop rule.
- The planning and end-of-work reviews (D4).
- Mutation-checking the tests a review adds.
