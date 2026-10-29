# Improve review after the item's tests pass (design T), 2026-10-27

Status: **design only; nothing built.** **§8 (2026-10-27) is the current proposal, amended by §9** (Astra's review, sound with changes): the owner's per-step iteration (build, test, document, Improve, commit for each step in turn). It supersedes the item-level order of §1 and §4 and the item-level flow of §7, and keeps their gates and evidence. §7 (2026-10-27) adds the gated flow: verify's checks become tests and gates,
and acceptance becomes a script step.

Consumer: first the owner, deciding D1 to D4 (§6) and E1 to E3 (§7), then the session that builds T. It sits beside
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

## 7. The gated flow: verify becomes tests and gates (proposal, 2026-10-27)

The owner: "Help me think through and define this: how you think you would do it, with an optimistic point of view,
and really look at this as we have gates to help us exit. The improve loop obviously would be done before
documentation. I do wonder if the verify stage should be incorporated as part of the tests or the gates in some way."

**7.1 What verify is today.** It is a model stage with four exit conditions (`shiploop_stage_spec`, row `verify`):
1. every completion criterion is confirmed after the last edit;
2. every recorded command exits 0;
3. each changed public entry point is traced with a valid, a boundary and an invalid input, and the latest review
   iteration found only trivial issues;
4. later-phase checks are marked pending with their owner.

Its script work:
- on entry: the change inventory and an advisory lint;
- at done: the lint gate and `test-rerun`.

Its done also triggers the item commit (`_item_commit`), and carry-forward reads its result.

**7.2 What verify found** (`verify-findings.txt`; time from `stage-minutes.txt`):

| run | what verify found | verify minutes |
|---|---|---|
| Sonnet 01b9b3 | a throwing store in `GET /api/new` escaped the handler and would crash the process; fixed, TC-11 added | 3.8 of 36.6 (10%) |
| Sonnet 491d9a | two untested but correct paths; TC_5 (b) and TC_9 (b) added | wall time includes sleep |
| Sonnet 36036c | nothing; no code changed | 0.7 of 32.5 (2%) |
| DeepSeek 759a03 | W1: one untested entry-point path; **W2: six material defects fixed**, including the `/api/new` crash and a New game race that reopened a won board; W3: none | 13.5 of 165.7 (8%) |
| DeepSeek 978478 | W1: three contract gaps closed; W2: the column refusals and the catch-all 404 asserted, one issue fixed; W3: nothing edited | 16.6 of 222.1 (7%) |

- **Every finding came from the entry-point trace,** a valid, a boundary and an invalid input per changed entry
  point, not from the criteria or the reruns.
- **Correction.** `test-stage-fixes.txt` had left 759a03 W2's in-flight lock unattributed; verify made it.
- So verify is a structured probe. It fixed defects in 3 of the 5 runs and closed test gaps in a fourth. Its
  mechanical half is two gates, lint and `test-rerun`.

**7.3 The proposal.** Each stage expects to pass once, and only a gate refusal makes it loop.

| stage | who works | exit gates (script) | on refusal |
|---|---|---|---|
| 1. Build: implement steps | model | lint gate, step Proof; each step's changed files recorded (design C) | the step fixes it |
| 2. Test: write, run, fix until green | model | base RED; every ID runs; floors; every command exits 0; mutation; lint; **new: the entry-point map** | the loop continues; unachievable goes back to step-plan |
| 3. Improve: one review per measured group | model | its own rule (a trivial pass); **moved here: lint gate and `test-rerun`** | the review fixes it |
| 4. Document | model | **moved here: lint gate and `test-rerun`**, which includes the doc checks among the recorded commands | document fixes it |
| 5. Accept | ShipLoop only | none of its own: the gates just held, so it records the evidence and makes the item commit | — |

Carry-forward follows, unchanged.

**Where verify's duties go:**
- **Criteria confirmed after the last edit.**
  - A criterion with a confirm-by command is a recorded command, and `test-rerun` at document's done is after the
    last edit by construction.
  - A criterion confirmed by inspection, with no command, is listed in the review's handoff. The review confirms it
    after its last edit, in its result.
- **Every recorded command exits 0:** `test-rerun` at Improve's import and at document's done.
- **The entry-point trace becomes tests.**
  - The test stage writes a valid, a boundary and an invalid case for each changed public entry point, titled as
    sub-cases of the closest quoted case. Duty 3 already asks for rejection cases.
  - The result maps them: `entry_points: [{"entry", "tests": [...]}]`.
  - The new gate checks that every entry point in ShipLoop's change inventory (verify's existing entry run, moved to
    the test stage) names three tests that ran. **Corrected (§9, row 7):** the change inventory lists files, not entry
    points, so the script checks the map's structure and the tests' IDs; whether every entry point is covered is the
    review's judgement.
  - The trace that found defects then becomes regression tests that the mutation check covers.
- **The latest review iteration is trivial:** Improve's own exit rule.
- **Later-phase checks pending with their owner:** a test-stage result field, which acceptance requires.
- **Assembling chained (ask-agent) work:** the item review, which reads the whole item.

**Why this is the optimistic shape:**
- Each stage's work is done once and judged by script.
- Acceptance becomes a gate, not a model stage, so each item reads one packet fewer. The 36036c test packet alone was
  45,540 bytes.
- When the tests are green and the review's first pass is trivial, the item goes straight through.

**7.4 Risk and how to watch it.**
- In 759a03 W2, verify was the last fresh look and found six defects. Under this flow they depend on two things: the
  entry-point tests, which the gate makes required, and the review after the tests.
- The live check therefore attributes every defect fixed to the stage that fixed it (test, Improve, document), and
  compares the totals with the baselines' verify findings above. A defect class that only verify used to catch, and
  that now ships, reopens the decision.

**7.5 Footprint.** Verify is woven into several places:
- the item commit trigger;
- carry-forward's `reads`;
- the `reconciliation` block;
- the packet counts (`SMALL_HOME_FINGERPRINTS`, e2e-efficiency);
- the Run Review stage catalog;
- the E2E metrics.

Removing it is the largest of T, C and this flow.

**7.6 Decisions:**
- **E1. Dissolve verify into tests and gates.** Recommended: yes. The alternative keeps verify as a slimmer model
  stage that only traces entry points.
- **E2. The entry-point gate.** Recommended: the map checked against the change inventory and the IDs that ran. The
  alternative is a duty with no gate.
- **E3. Build order.** Recommended: T, C and this flow in one batch, with one release and one verification run per
  model, and per-stage defect attribution in the report, so the batch can still be read. The alternative is
  separate releases, each measured alone.

## 8. One iteration per step: build, test, document, Improve, commit (current proposal, 2026-10-27)

**Revised the same day.** The first version ran Improve before document. The owner then:
- moved Improve after document;
- asked that the test stage be defined as building out the test specification;
- asked that every linter run on the production code after build and on the test code after the tests are written;
- asked that the test stage build mocks that simulate the expected behaviour before the system tests;
- added a knowledge stage after Improve, which updates the environment, the architecture decisions and the spec
  clarifications, and decides whether a reusable skill should be written;
- asked that the stage prompts name the existing skills that can help build or test.

8.2, 8.2a, 8.2b, 8.2c and 8.3 say what changed.

The owner, in five messages:
- "To be very clear, I want to build one step, then test, improve, and document, and then build step number two,
  then test it, improve it, document it, and so forth and so forth. The goal is not to just do one monolithic build of
  all the steps."
- "We should have a very specific stage which is like 'commit all the changes,' not just 'verify.' 'Verify' is too
  generic."
- "We should commit on every iteration right after the documentation."
- "I think the improve step should come after document, and we should clear that the tests should build out from the
  test specification. The test specification should actually build out the tests themselves, performing the tests,
  looping as needed."
- "Do we need to be more detailed because I don't see the linters running, which they should run after the code has
  been built?"
- "Technically, we should run every linter after the test code is written as well, so linters should be done both in
  production code and test code. We should also be clear, in the test areas, that we want to build mock objects
  simulating the behavior we expect before going to system tests."
- "We probably need a step also at the end: do we need to update the environment or architecture decisions, or
  identify that we've actually clarified some of the spec requirements (which may have been vague), as a step after
  the improve stage"
- "I think we also wanted to determine if, after the improve stage, there are any skills that should be written so
  that they could be reused for repeated stages later. Likewise, we wanted to make sure that we had the prompt
  template reference any skills that might exist that could help us execute in the build stage or test stage, if
  needed. I don't know if those are just in the prompt templates or somewhere else."
- Earlier (memory `todo-step-series-order`, 2026-10-17): each planned step runs its own series, in plan order.

**8.1 The shape.**

| when | stages | who works |
|---|---|---|
| once per item, before the steps | step-plan; test-spec, which specifies every case (its ID, oracle, RED and GREEN) and assigns each to a step; validate-existing | model |
| **for each step, in plan order** | **build → test → document → Improve → knowledge → commit** | model, except commit: ShipLoop only |
| once per item, after the last step | carry-forward: the future queue and the item's learnings | model |

- Verify is retired. The commit stage replaces it and is named for what it does.
- The knowledge stage follows Improve, so it records what the review taught as well as what the step decided.
- The commit stage comes last. It is still the commit "on every iteration right after the documentation": the
  documented, reviewed and recorded step goes into one commit.
- The next step's build starts from that commit.

**8.2 Each stage and its exit gates** (all run by ShipLoop; a refusal returns to the same stage):

| stage | the work | exit gates |
|---|---|---|
| build | write this step's code, using the skills the packet lists for it (8.2c) | **lint the production code** (8.2a); the step's Proof |
| test: build out the test specification | using the skills the packet lists for testing (8.2c), build mocks that simulate what the step's dependencies are expected to do; turn each test-spec case assigned to this step into a test against them, titled with its ID and asserting the case's oracle (never the code's current behaviour); add a valid, a boundary and an invalid case for each entry point the step changed; lint the test code; perform them by running every recorded command; loop: fix the code, or a test for a recorded independent reason, until one run after the last edit passes every gate | **lint the test code and any production code the loop changed** (8.2a); the tests pass; IDs; floors; RED against the code before this step; mutation of this step's changed lines; the entry-point map |
| document | update the docs this step's change affects, from the behaviour the tests now show | lint on docs; the doc checks among the recorded commands |
| Improve | review the whole step together (code, tests and docs), now green and documented. A behaviour fix adds a test for it and corrects the docs it affects; a doc that disagrees with the code is a finding. Rerun every command after each edit | its own rule (a pass that changes nothing material ends it); at import: lint and a rerun of every recorded command, doc checks included |
| knowledge | update the knowledge home from what this step decided and the review taught (spec clarifications, satisfied-by lines, architecture decisions, environment facts), and make the step's skill decision (8.2b) | each knowledge file is changed or carries a no-change reason; each spec edit names its requirement and its source; a change of intent carries an open item; new AD IDs are unique; the skill decision's shape and repeat evidence; lint on the knowledge files |
| commit | ShipLoop commits everything the iteration changed (code, tests, docs, review fixes, knowledge, any skill) as one `feat(<item>/<step>)` commit. Its message carries the step's learnings and decisions, the review's lessons and the evidence. | none of its own: it checks that the tree is the one the knowledge stage's gate ran on |

**The test stage, defined.** The test specification is the source of every test. The test stage builds out this
step's part of it into tests, performs them, and loops until they pass:
1. **Mock the dependencies first.** For each thing the step's code calls, build a mock (a test double) that simulates
   the behaviour the spec expects, including slow, failing and out-of-order answers. Examples are the network, the
   clock, randomness, storage, a child process and browser APIs. The step's code is tested against the mocks. Real
   boundaries are left to the system tests (the outer `system-test` stage), and each mock records what it stands in
   for, because a mock proves the code only against the behaviour it simulates (`testing-and-documentation.md`).
2. **Build out:** one test per assigned case, titled with its ID, asserting the oracle the spec states.
3. **Lint the test code:** run `shiploop lint --action` over the tests just written. The stage's done runs the lint
   gate on them (8.2a).
4. **Perform:** run every recorded command, which covers this step's focused tests, the earlier steps' tests and the
   regression suite.
5. **Loop:** for each failure, find its cause with one small observation and fix the product. Change a test only for
   an independent reason recorded in the notes. Never weaken, delete or skip one. Repeat until one complete run after
   the last edit passes every gate. There is no iteration limit.

The stage's Goal line says exactly this: §2's wording, scoped to the step's cases. The test-spec stage itself still writes no test code: it fixes what
each test must assert before any code exists, so a test asserts the spec, not whatever the code does.

The gates in the test row, in plain terms:
- **The tests pass:** every recorded command exits 0. This is "run the tests and see if they pass".
- **IDs:** every planned case was written, carries its ID in its name, and actually ran. A skipped test, or a filter
  that matches nothing, is not passing evidence.
- **Floors:** no command runs fewer tests than it did before, so a run cannot get green by deleting or skipping
  tests.
- **RED:** ShipLoop runs the new tests against the code as it was before this step, in a temporary checkout. There
  they must fail. A test that already passes there does not test this step's code.
- **Mutation:** ShipLoop makes one-token changes to this step's changed lines, for example a flipped comparison. It
  applies each alone in a temporary copy and reruns the focused tests, which must notice. A mutant that survives needs
  a test that kills it, or a recorded disposition: equivalent, out of scope, or not exercisable
  (`shiploop_mutation.mutation_check`). A run that kills no mutant at all is refused even with dispositions (§9). It is the check that the tests would catch a bug. It refused at least once in
  every one of the five runs (`gate_counts.mutation_not_done`: 2, 1, 1, 3 and 4 times).
- **Entry-point map** (new, §7.3): each entry point this step changed has its three cases, and they ran.

**8.2a Where the linters run.** ShipLoop runs them itself (`shiploop_lint`). The model also runs
`shiploop lint --action` after each edit, which only reports.

| after | what is linted | what the gate does |
|---|---|---|
| build | the production code this step changed | applies safe auto-fixes to the lines the step changed, refuses once so the model sees them, then refuses while a new finding on a changed line has no waiver (`lint_waivers`, with a reason) |
| test | the test code just written, and any production code the loop fixed | the same, before ShipLoop's own test runs |
| document | the docs this step changed | the same, where the repository configures a docs linter |
| Improve (import) | the review's edits, in code, tests or docs | the same, then a rerun of every recorded command |

- **Which linters.** "Every linter" means every linter the catalog finds for each changed file's type:
  - built in: ruff (Python) and shellcheck (shell);
  - whichever of these the repository configures: eslint, prettier, tsc, mypy, black, markdownlint-cli2, yamllint,
    gofmt, clang-format, terraform fmt, ktlint, phpcs, rubocop, plus actionlint whenever it is on PATH;
  - `npm run lint` or `make lint`, when a changed file has no other linter.

  ShipLoop never installs one.
- **Per step, "a changed line" is this step's line.** Today the gate compares against the work item's base. In the
  iteration it compares against the iteration's base, the previous step's commit.
- **The gap the runs show: a project with no linter configured gets syntax checks only.** In 36036c every step's lint
  gate passed. Its coverage lines read:
  - `game.js` and `server.js`: "syntax checked by node --check (no catalogued linter)";
  - `public/index.html`: "not in scope: no catalogued linter for this file type; git diff --check only"
    (`RUN/lint/nav-ecd62913….gate1.md`).

  A green lint there meant "it parses". So each stage's packet and the run's report print that coverage line beside
  the lint result, and a reader never takes a syntax check for a lint.

**8.2b The knowledge stage, defined.** It keeps the knowledge home true after each step, so the next step's
packets read what this one learned.
- **Spec (`KNOWLEDGE/spec.md`).** Each edit names the requirement ID and its source: a test case ID, an AD or a review
  finding. It is one of three kinds:
  - **clarified:** a vague requirement made precise by what the step decided, stated as observable behaviour;
  - **satisfied by:** the requirement, the files and step that meet it, and the tests that show it. 36036c wrote these
    for every requirement, but only at carry-forward;
  - **changed:** the requirement's intent itself moved. That is never silent. **Corrected (§9, row 1):** as today
    (`knowledge_home.step_spec_refusal`), it is a send-back to step-plan, not an open item.

  Stack choices stay out of the spec and go to architecture, because the two are orthogonal.
- **Architecture (`KNOWLEDGE/architecture.md`).** A decision the step made or changed becomes a new `AD-<n>`, or
  refines or supersedes one. A superseded AD keeps its text and gains a status, and is never deleted.
- **Environment (`KNOWLEDGE/environment.md`).** What the step learned about running and testing:
  - commands;
  - the harnesses and mocks the test stage built, with what each simulates;
  - platform facts;
  - the lint coverage line (F6).

  The test stage's duty 2, recording harness decisions, moves here.
- **The skill decision.** It is today's carry-forward rule, made after every step instead of once per item:
  - Inspect the repository's skill index and the host's skills.
  - Decide, smallest first: `none`, `reuse`, `update` or `create`.
  - `update` or `create` only when the same procedure ran in two or more steps or items, or a pending item or R-n says
    it will recur, citing those IDs.
  - The skill goes in the repository's skill directory and is listed under `## Skills`.

  Made per step, a skill written after S2 is in the packets of S3 onwards (8.2c). Made per item, it reaches only
  later items.
- **What the runs show.**
  - The knowledge home already changes during the build, at scattered points:
    - at carry-forward: spec and architecture in 36036c, spec in 491d9a;
    - after document in 978478;
    - inside W2's item commit and the end-of-work review in 759a03.

    The stage gathers these into one place per step.
  - Across 13 recorded runs, all 20 carry-forward skill decisions were `none`. The only repeat any noted was 978478
    W3's: "The only procedure that ran twice (driving Chrome over CDP …) is a host capability". So the forecast is
    mostly `none` per step, with the gain in projects whose steps do repeat a procedure.

**8.2c Skills in the stage prompts: where they are today, and the proposal.**

| where | today |
|---|---|
| prepare (discovery) | checks the repository's index, README and AGENTS for skill links, and records fit or no fit under `## Skills` in environment.md |
| step-plan | each step lists `skills: [{"name", "why", "locator"}]`, after rereading the host's skills and the repository's index ("an earlier item may have added one") |
| implement (build) packet | prints them in the Step block: "Skills (use each; the summary says whether you did): …", and duty 2 says "Use each listed step skill for its purpose (invoke it, or read its SKILL.md and follow it)" |
| test, document and Improve packets | **name no skill.** The test packet says only "never assume a named skill or MCP is available" |
| carry-forward | the reuse or write decision, once per item |

So skills are in the prompt templates for build only, by way of the step plan. Every one of the 51 steps planned
across the 13 runs listed none.

**Proposal:**
- Every model stage of an iteration (build, test, document, Improve) prints one **Skills for this step** block. It
  holds:
  - the skills the step plan listed for the step;
  - any skill a knowledge stage created or updated earlier in the run;
  - the `## Skills` entries of environment.md that fit.

  Each entry gives its name, why and locator, and the packet points at the SKILL.md rather than copying it.
- A step plan row's `skills` entry gains an optional `stages` field (build, test, document, Improve; default build).
  A test-facility skill then shows in the test packet, where it is used.
- "Never assume a named skill or MCP is available" stays: it forbids unlisted ones, not listed ones.

**8.3 What changes from today:**
- **Tests per step, built out from the spec.** Today they are written once per item, after every step. The
  test-spec assigns each case to the step whose code it tests. A case that needs several steps goes to the last of
  them.

  This also fixes the cause in `todo-step-series-order`. There, item-wide checks could not pass on S1, so a chess run
  collapsed three steps into one. A check bound to its step is due only when that step is done.
- **Evidence the model wanted it.** In 36036c Sonnet planned it this way itself. Its item context says "Order: (1)
  test/game.test.js TC-7,8,9,12,13,14 then game.js; (2) test/helpers.js + test/server.test.js … then server.js; (3)
  public/index.html with TC-4; (4) test/browser.test.js TC-15", and ShipLoop's stage order deferred every test to
  after S3.
- **Mocks before system tests.** No battleship run built a mock of a dependency. They did inject one simple double, a
  seeded or extreme random-number source (`createGame({ rng: mulberry32(7) })` in 36036c). In 01b9b3 an extreme
  source caught the placement loop that never ended.
  - The page's network was never mocked. Sonnet's stale fire reply, which shipped twice, needs exactly that: a mock
    `fetch` that holds a reply until the test releases it, so the test can press New game while a shot is in flight.
  - DeepSeek's 759a03 reached the same case only through a real headless Chrome with 600 ms of emulated latency
    (`browser-check/page.js`).
  - A mock makes the race a fast, deterministic component test, before any system test.
- **Lint on both sides.** Production code is linted after build; test code after the test stage writes it (8.2a).
- **A knowledge stage per step.** It updates spec, architecture and environment and decides the skill, every step.
  Carry-forward keeps only the future queue and the item's learnings, and its skill decision moves to the knowledge
  stage, so the decision is made in one place.
- **Document, then Improve.**
  - The review sees the step whole: code, tests and the docs that describe them. A doc that disagrees with the code
    becomes a review finding, not something nobody checks.
  - The review is the iteration's last edit, so its final gate is the gate the commit relies on.
  - The cost: a review fix that changes behaviour must also correct the docs, and the review's handoff says so.
- **A review per step, after its tests and docs.** This returns to the count from before P0.
  - Design C is not needed: each step is reviewed on its own change.
  - B's declared-path rule goes.
- **A document stage per step.** It is left out when the step changed no behavioural path (the existing left-out
  rule).
- **One commit per iteration, as the last stage.**
  - It replaces three kinds of commit today: the step commit before Improve, the review's own commits, and the item
    commit at verify.
  - On this route the review leaves its edits uncommitted for the commit stage; the improve skill's route already has
    a no-commit request.
  - The look-back reads one commit per step, holding everything that step learned.
- **Each iteration starts from a commit.** The next step's base is HEAD, so its RED check, review diff and look-back
  each name one step.

**8.4 Cost, stated with the runs.**
- Per-step reviews come back:
  - Sonnet: 3 reviews, not 1, about +1 to +2 awake minutes (01b9b3's three took 2.7);
  - DeepSeek: 12, not 3, for a plan like 978478's. Its per-step reviews before P0 took 28.1 minutes, against 10.4 for
    759a03's three item reviews.
- Each item also gets a test and a document stage per step, not one of each.
- What keeps this optimistic:
  - a step that changed nothing gets none of these (P4);
  - a review whose first pass is trivial ends after one pass;
  - each step's tests and mutants cover one step's lines, not the whole item;
  - verify's stage and packet are gone.
- **Prediction to measure:** after green tests and written docs, more step reviews end on a trivial first pass than
  the 8 of 12 seen in 978478 before P0.

**8.5 Decisions for the owner:**
- **F1. Cases assigned to steps in the test-spec.** Recommended: yes, with a gate that every case names a step of the
  plan.
- **F2. One commit per iteration, the review's edits folded in.** Recommended, as asked. The alternative commits
  after test as well, so the review's commits stay separate.
- **F3. Accept the per-step cost, and measure it.** Recommended: yes, with one Sonnet and one DeepSeek battleship run.
  The report shows each stage's minutes per step, and which stage fixed each defect.
- **F4. Where the test code is written.** Recommended: in each step's test stage, from the spec, after the step's code
  (above). This matches the owner's order "author the code, do the tests, make the code fit the tests". The
  alternative is test-first: the test-spec stage writes each step's tests before its build, RED by design, and the
  build loops until they pass.
- **F5. Mocks before system tests.** Recommended: the test spec names, per case, the mock it runs against (what it
  simulates, and the slow, failing or out-of-order behaviour it plays). The test stage builds those mocks first. Start
  as a stage duty plus that test-spec field, and add a gate only if the live run shows cases skipping their mock.
- **F6. Lint coverage shown.** Recommended: every lint result prints its coverage line, so "syntax only" is never read
  as linted.
- **F7. A knowledge stage per step.** Recommended: yes, with the gates in 8.2. A spec change of intent always carries
  an open item.
- **F8. The skill decision per step,** moved from carry-forward. Recommended: yes, keeping today's repeat-evidence
  rule.
- **F9. Skills in every iteration packet,** with the optional `stages` field, the knowledge stage's included (§9).
  Recommended: yes.

## 9. Astra's review of §8, and the changes it makes (2026-10-27)

Astra reviewed §8 at max effort in a read-only sandbox (`gpt-6-astra`, no fallback). Its verdict: **"sound with
changes. The order is coherent; the proposal needs stronger contracts for iteration identity, final verification,
and evidence retention."** The question and the answer, verbatim, are in
[`astra-review-20261027.md`](experiments/e2e-review-after-tests-20261027/astra-review-20261027.md).

I checked each finding against the code before taking it. Every P1 and P2 holds where I checked it:

| # | finding | checked against | what changes in §8 |
|---|---|---|---|
| 1 (P1) | The knowledge stage could change a requirement's intent, or add an executable skill, after the last verification | `knowledge_home.step_spec_refusal`: an implement step may only add acceptance lines inside an existing R-n, each ending with its step marker such as `(W1/S2)`; changing or removing a line "changes the contract, which is the step plan's to decide: the refusal names send-back" | The knowledge stage keeps that rule. Clarified and satisfied-by entries are additions carrying the step marker. **A change of intent is a send-back to step-plan, not an open item** (this corrects 8.2b). A skill that adds executable files gets the lint gate and its own check at the knowledge stage's done |
| 2 (P1) | A step currently advances when its build is accepted, and one Improve child is bound to the current producer | `implement_progress` counts accepted implement actions since the step plan; `validate` requires `active_improve.action_id` to be the current action | An **iteration identity** (item, plan revision, step, base) is carried through all six stages, and the step advances only after its commit. Improve's child binds to document's action; an omitted document's not-applicable record goes through the same checkpoint. The ask-agent route gets the same step boundaries (G1) |
| 3 (P1) | Commit must be a recoverable gate, and other code also commits | `_item_commit` fires on verify; `_step_commit` tolerates failure; `_skill_commit` and `_knowledge_close` also commit; `commit_scope` leaves undeclared non-doc files, such as a new skill's scripts | **Within an iteration only the commit stage commits.** Improve runs with no-commit for its passes and its completion, and the knowledge-record and skill commits are suppressed. The commit stage persists a pending operation, checks the parent and the tree, retries idempotently, and the step advances only on success. Skill files are in its scope |
| 4 (P1) | Assigning cases to steps is not enough for RED and GREEN | `stage_commands` gives the item's commands to test and verify; `new_ids`, `accepted_counts` and `floors` are item-level | For each step there are three sets: the commands active so far; **GREEN**, every case due so far; and **RED**, only this step's newly due cases, against the iteration base. `red_na` stays for characterization and test-only steps. A spanning case is due at its last dependency. The iteration base is threaded through the base check, mutation and lint. Tests a review adds are registered by ID, so the reruns include them |
| 5 (P1) | Send-back and no-change are underspecified | `stage_spec._finish` uses `verify` as the send-back range's end | Each stage's send-back states which base survives, which receipts it invalidates and how retained edits are revalidated. A stage is skipped only when its obligations are already met, not merely because build changed nothing |
| 6 (P1) | Earlier steps' evidence and obligations can disappear | `planning_revision.current_actions` keeps the latest done result per (item, stage); `_ITEM_RECORDS` gives system-test-author the item's one test result | **One revision-aware aggregate** of every step's receipts and open obligations. Carry-forward, system-test-author and the reconciliation verify did all read it. Each mock maps to a real system case and its owner |
| 7 (P2) | Several "script gates" are model judgements in disguise | `lint.inventory_writes` records changed files, not entry points; `_check_skill_decision` accepts any nonempty evidence strings | **Correction to §7.3 and §8.2:** the change inventory is a list of files. Scripts check structure: map rows name real changed files and executed, distinct test IDs; AD IDs are unique; skill evidence names real step or item IDs where the procedure ran. Whether every entry point is covered, how an intent is classified and whether two procedures are the same are the review's judgement, and the packets say so |
| 8 (P2) | Run Review needs more than a catalog refresh | `export.stage_model` reads every state version from 5 up with today's tables | A new lifecycle version (v6). Run Review renders it per step and still reads older runs. Fresh runs only, with no migration of saved states (one supported version) |
| 9 (P2) | §8.4 is not a total-cost forecast | My recount: P0's item flow for three steps is 7 model actions (three implement, one Improve, test, document, verify); §8 is 15 (five per step) | §8.4 becomes a **pilot** that measures non-overlapping model time and packet volume. The cheapest faithful shape keeps the order with compact step packets, shared harnesses, reuse of unchanged receipts and a script-only commit |

Nits, also taken:
- **Lint.** Lint can be `off`, or a tool can be unavailable or time out; the coverage line (F6) reports both.
- **Mutation.** A run in which no mutant is killed is refused even when every survivor has a disposition. Dispositions answer survivors only once at least one mutant was killed (this corrects 8.2's wording).
- **Skills block.** F9's skills block includes the knowledge stage's packet.

**9.1 Build order** (Astra's, which I adopt):
1. Specify the iteration identity, producer ownership, retry invalidation and the final-tree commit invariant.
2. Implement one two-step lifecycle, including an omitted document stage and the ask-agent route.
3. Add due-case projection, cumulative floors, shared baselines and obligation aggregation.
4. Exercise send-back, commit failure and retry, test-only steps, cross-step cases and tests a review adds.
5. Update the packets and Run Review (v6, with older runs still read). Then run the two pilots, with stage-level
   defect and cost attribution.
6. **Once the lifecycle is complete, update the README** (owner, 2026-10-28: "Once complete, we should update the
   README with the updated detailed status"). Two parts go into `skills/shiploop/README.md`:
   - **The lifecycle in detail.** Rewrite the "Navigator: producer, Improve child, then transition" section, which
     today lists "the 8 inner stages in 5 phases" with `implement` once per step. It covers:
     - the per-step iteration (build, test, document with its review, knowledge, commit);
     - each stage's gates, the lint points and mocks before system tests;
     - the skills block, and the commit stage in place of verify.
   - **A status section in the owner's frame.**
     - Plan: the build order.
     - Accomplished: each step, with its evidence.
     - In progress.
     - Pending: what still waits on the owner (the F and G decisions), and the pilots' results.
     - A small dependency picture of the steps.

   It lands with the change that completes the lifecycle, so the README never describes a flow the code does not run.

**Step 1 done (2026-10-28): the iteration contract.** `skills/shiploop/scripts/shiploop_iteration.py` specifies the four
invariants as pure functions. `test/shiploop-iteration.test.py` pins them: 24 tests, written first and failing on the
missing module.
- **Identity.**
  - `Iteration` holds (item, plan revision, step, number, base).
  - `start` takes the plan's next uncommitted step, in plan order, from HEAD; `advance` gives the next base.
  - A base is always a full commit ID. It is never a snapshot of a dirty checkout, so edits that a send-back leaves
    behind count as the next iteration's change.
  - `stale` marks a receipt recorded for another identity.
- **Producer ownership.**
  - `STAGES` is implement, test, document, knowledge, commit. The stage IDs keep `implement` for build.
  - `MODEL_STAGES` holds every stage but commit, which is ShipLoop's alone.
  - `owns_improve`: document owns the review.
- **Retry invalidation.**
  - `invalidated`: a send-back voids its target's receipt and every later one.
  - `ends_iteration` and `after_send_back`: a send-back inside the iteration keeps its base; one to planning ends the
    iteration.
  - Commit is never a send-back target.
- **The final-tree commit invariant.**
  - `pending_record` is written before the commit.
  - `commit_decision` commits the gated tree on the base, and refuses a tree that changed after the knowledge gate,
    reopening knowledge.
  - It recognises a commit that already happened, and refuses any other commit: only the commit stage commits.

The navigator does not use it yet. Step 2 wires it in.

The build stays on a feature branch until the lifecycle is complete, so no release from main ships half of it.

**Step 2 plan (2026-10-28).** Step 2 is the lifecycle switch, and its reach is wide. Today `"verify"` appears in 96 test
files and 11 ShipLoop modules, and in Run Review and the E2E audit harness. The per-step test stage also needs each
case's step. So step 2 runs as three sub-steps, each a commit whose tests pass, on the feature branch:
- **2a. Due cases per step,** pure, in `shiploop_iteration`. **F1 needs no new field:**
  - each test-spec case already names its step-plan `criterion`;
  - each step already lists the `criteria` it satisfies;
  - so a case is due at the last step that lists its criterion, and a case no step lists is due at the last step.

  For each step, ShipLoop derives:
  - **due cases:** every case due so far, which must be GREEN;
  - **new cases:** this step's cases, the only ones RED applies to;
  - **active commands:**
    - a focused command runs from the first step one of its IDs is due, narrowed to the IDs due by then;
    - a check command runs from the last step that lists its criteria;
    - the regression command runs at every step.

  On 36036c's real plan:
  - **S1:** the game tests;
  - **S2:** the server tests, and the docs check (it names C4 and C8);
  - **S3:** the page's server test (TC-4) and the browser test.

  Floors per step stay step 3's.
  **2a done (2026-10-28):** `case_step`, `due_cases`, `new_cases` and `active_commands` in `shiploop_iteration`. Nine
  fail-first tests in `test/shiploop-iteration.test.py` pin them on 36036c's plan, 33 tests in all. The navigator does
  not use them yet.
- **2b. The navigator switch.**
  - The per-step stage sequence runs through `shiploop_iteration`, with the identity in the inner loop's record and
    the step advancing after its commit.
  - Rule `item` moves to document, so document owns the review.
  - The knowledge stage gets its row and packet.
  - The commit stage becomes a script step with its pending record. Verify is retired, and carry-forward follows the
    last iteration.
  - The test stage runs 2a's active commands, with RED on the new cases against the iteration base.
  - The omitted-document route is covered.
  - Every test that pins the old flow is updated in the same change, so there is one supported version.
  2b runs in five increments, each a commit whose tests pass:
  - **2b-1, done 2026-10-28.** Each inline step records its iteration in `RUN/iterations/<item>.json`, which
    `current_iteration` reads, and the step commit records the step's commit beside it.
    - The base is HEAD at the end of the call that entered the step, after that call's step, preparatory, skill and
      knowledge commits.
    - It cannot be taken earlier, because `_transition` runs before those commits.
    - Bookkeeping only: the flow is unchanged. One fail-first CLI test covers it (a three-step walk), and the quick tier
      passed 33 suites.
  - **2b-2, done 2026-10-28.** Test and document run after each step:
    - the test stage runs 2a's active commands, with RED on the new cases in a checkout of the iteration's base;
    - document's left-out rule reads the step's diff since the base;
    - rule `item` moves to document;
    - the next step's implement follows document.

    Verify still closes the item, for now. What landed:
    - **Order.** `_next_step_follows` routes an inline document to the next step's implement while steps remain;
      `step_view` names the step just built at test and document, and the step to build at implement.
    - **Base per step.** `_iteration_base` recaptures `lint.capture_base` when document hands over to the next
      implement, after `_step_commit` has committed the step. Lint, mutation, the RED base check, the left-out rule
      and the review diff all read it, so the second step's lint gate sees only its own lines: a finding the first
      step waived is in that step's commit (`GateTests.test_every_implement_step_is_gated`).
    - **Review.** Rule `item` is on document. The review prints the Step block, implement's guides beside its own,
      and the review base since the step began; it leaves its edits uncommitted
      (`STEP_REVIEW_NO_COMMIT`), and its import reruns the step's focused command when it changed a file. A step
      whose document stage records `changed: false` starts no review.
    - **One commit per step.** `_step_commit` runs in `_transition` once the step's document row is accepted. The
      knowledge close no longer splits a step's spec line out of it.
    - **Reads.** Document quotes the step's due cases, so it reads the item's test-spec result (consumer contract:
      a quoted key's producer is among the reads). The review receipt is document's product now, and verify reads
      each step's document result, so its packet still lists the step reviews it builds on. Head budgets: document
      +75 characters, verify +207 (`test/shiploop_e2e/head_table.json`).
    - **Removed.** The wide-item rule (`step_path_groups`, `_wide_item`, `_item_steps`, `_review_steps`) and the
      implement-stage review. The references (README, navigator.md, improve-stages.md, glossary) say so; the
      replay harness's literal schedule parks document.
    - **Left for 2b-5.** Lint's gate text still says "lines this item changed": under per-step bases those are the
      step's lines since its base. The test and document packets do not print the Step block (F9). (Run Review's
      stage catalog and card text follow the new schedule already.)
  - **2b-3. The step's reflection, done 2026-10-28 (option C).** The owner chose C ("Go with C", 2026-10-28): no
    knowledge stage. What landed:
    - **Document reflects.** Its duty 3 is now *Reflect*: with the step built, tested and documented, it records what
      the step showed in the knowledge home. That means a marked line in the R-<n> entry it concerns (a clarified
      clause, or the files and test file that now meet it), a decision implement did not record (a new AD-<n>), and a
      command, harness or platform fact. It routes new work: a defect in the step is fixed now, work the step plan
      lacks is a send-back, work a later step holds is left to it, and work outside the item is an open item due at
      carry-forward. Document's packet names the step and its mark (`_document_step_lines`) and lists all three
      living files (`knowledge.READS`, `STAGE_FILES`). Its done-when gains "the knowledge home records what this step
      showed, and `knowledge` names each living file with what changed in it or why nothing did".
    - **The knowledge record.** A done document result carries `knowledge`: exactly `spec`, `architecture` and
      `environment`, one per living file, each nonblank (`KNOWLEDGE_RECORD`, `_canonical_handoff`). The keys are not
      file names, because a result template must print no product-like file name (packet-completeness). A missing one is refused ("Add
      knowledge to …"). The step commit prints it as its Knowledge home section (`step_commit_message`).
    - **Open items.** Document joins `OPEN_ITEM_STAGES` and `CARRY_FORWARD_PRODUCERS`. `open_items` lists every step's
      document result since the item's latest send-back (`PER_STEP_STAGES`, `_step_actions`). Astra's finding was
      verified: `current_actions` keeps one result per (item, stage), so S1's rows would have dropped out at S2.
    - **Gates on the final tree.** `_step_spec_refusal` runs at implement's and document's complete and at the step
      review's import. Its refusal now says "In a step, spec.md takes only new lines inside an R-<n> entry the committed
      spec holds". The review's focus covers the knowledge edits and its import checks them, so the step commit holds a
      tree a gate ran on.
    - **Contract.** `iteration.STAGES` is `implement, test, document, commit`. The commit decision reopens document
      when the tree changed after the last gate.
    - **Packet size** (`test/shiploop_e2e/head_table.json`). Inline document grows 13,594 -> 15,976 characters and is
      still printed whole. Ask-agent document's whole grows 15,162 -> 17,544, so it now prints as a 13,626-character
      head that keeps the duties and gates and leaves out the optional lookups, as the other heads do. The due-stage
      placeholder adds 10 characters at test-spec, verify and carry-forward.
    - **Kept as reported, by decision.**
      - *The not-applicable document skips the reflection.* A step whose change touches no code or test path has no
        observed behaviour to reflect on. Implement's and test's own write-backs stand, and carry-forward reconciles
        the knowledge home at the item's end.
      - *Test writes the knowledge home too.* Test records the harnesses it builds, at the time it builds them.
        Document reflects on what remains.
      - *The skill decision* stays once per item, at carry-forward.
    - **Not done.** No unique-AD-ID gate. It waits for a run that shows a reused AD ID; `knowledge.check` already
      refuses a dropped one. Lint on the knowledge files stays with the commit stage (2b-4).
    - **Evidence.** Fail-first tests, each seen failing before the code:
      - shiploop-handoff `test_each_steps_document_keeps_its_open_items_until_its_items_carry_forward` and the
        `knowledge` shape rows;
      - shiploop-navigator-contract `StepReflectionCliTests` (three CLI tests);
      - shiploop-actual-improve-cli `test_a_step_reviews_unmarked_spec_line_is_refused_at_its_import_and_a_marked_one_is_imported`,
        which fails with the import gate disabled;
      - shiploop-iteration's stage order and commit decision;
      - shiploop-knowledge's writer pins.

    Option A's cut, superseded 2026-10-28 by the owner's choice of C (kept for the record):
    - **Row.** `knowledge` is an inner model stage after document, on both routes (once per item on the ask-agent
      route until 2c). It writes the knowledge home (spec.md, environment.md, architecture.md) and the skill, and
      nothing else.
    - **Result.** `knowledge` names each of the three files with what changed or why nothing did; `skill` is
      carry-forward's decision, unchanged in shape.
    - **Gates at done.** Each file named with a non-empty line; the spec only gained lines inside an existing R-n,
      each ending with the step's marker (`step_spec_refusal`, whose refusal names send-back); no AD ID is used twice in
      architecture.md; the skill decision's shape and repeat evidence (`_check_skill_decision`, moved).
    - **Routing.** The iteration's last model stage is knowledge: `_next_step_follows` keys on it, the step commit
      fires when it is accepted (so the step's knowledge and any skill are in the step's one commit), and the base is
      recaptured when it hands over.
    - **Carry-forward** keeps the queue and the item's learnings; its skill decision goes.
    - **Not in 2b-3.** Lint on the knowledge files and the test rerun before the commit are the commit stage's
      (2b-4), which checks the tree the knowledge gate ran on.

    **Reopened 2026-10-28, decided C the same day (the owner).** The owner asked: "Do we need to introduce a stage at all
    during the sequence after we implement? To say, do we need to update the architecture environment or anything that
    we've sort of more well understood about the specs? Just as a reflection to determine if the definitions need any
    updating as well, do we need to introduce a consideration of whether there are any more tasks that should be
    added?"
    - **Option A** is the cut above: a `knowledge` model stage after each step's review.
    - **Option C:** no new stage. Document becomes the step's one place to reflect and record knowledge. The step
      review corrects that knowledge and writes back what it finds. The gates run on the final tree at the step
      commit. A step may record follow-up work as open items for carry-forward. The skill decision stays per item at
      carry-forward.
    - **Astra (gpt-6-astra, max effort) recommends C with three additions:** the review writes its corrections back,
      every step's open items are kept, and the gates check the final tree. Evidence:
      `docs/experiments/knowledge-stage-review-20261028/astra-review.md`.
    - **Its reasons:**
      - C keeps the knowledge edits inside the change the review already examines. A adds a writing action after the
        review (§9 rows 1 and 7).
      - A costs one model action per step: 15 against 12 on a three-step item.
      - All 20 recorded skill decisions were `none`.
    - **What C loses:** a skill created after one step for use by the next.
    - **Revisit A** when a pilot shows C missing knowledge, or a skill reused within one item.
    - **Its findings:**
      - **Verified and fixed** (`07585d1a`): the spec gate took its R-n spans from the edited text, so a step could
        add a marked `R-2`.
      - **Reported, then checked in 2b-3:**
        - document is in neither `OPEN_ITEM_STAGES` nor `CARRY_FORWARD_PRODUCERS`: true, fixed;
        - `current_actions` keeps one result per (item, stage), so S1's open items vanish once S2 submits: true, fixed;
        - `_document_entry`'s N/A route would skip the reflection: true, kept by decision (above);
        - the step commit message carries only implement's learnings: true, fixed (Knowledge home section);
        - test is a third knowledge writer: true, kept by decision (above).
  - **2b-4. The commit stage.**
    - It replaces the step commit, the review's commits (Improve without commit), the knowledge-record commits inside
      an iteration, and verify's item commit.
    - It uses `pending_record` and `commit_decision`.
    - Verify is retired, and carry-forward follows the last iteration.

    It lands as two commits whose tests pass: 2b-4a, the commit stage; then 2b-4b with 2b-4c, verify's gates moved
    into the step and verify retired. (2b-4b was cut as its own commit first; its quick tier showed the same packet
    pins and heads failing that retiring verify changes again, so the two land together.)
    - **2b-4c, 2026-10-28: verify retired.** The stage table has 23 stages; each item runs step-plan, test-spec and
      validate-existing, then implement, test and document per step, then carry-forward (`_finish`: send-back from
      test-spec through document). State version 10; a version-9 run is refused with `V9_REASON`.
      - **Where verify's duties went** (§7.3, checked against its duty text):
        - *Run and Confirm* (every recorded command after the last edit; each criterion confirmed): document's rerun
          and the review import's rerun. A criterion no passing command confirms is the step review's, by inspection
          after its last edit (a new bullet in its focus).
        - *Trace* (one valid, one boundary and one invalid input per changed public entry point): a new step-review
          bullet, and the test stage's duty 3 now writes those three cases. Every finding verify made in five runs came
          from this trace (§7.2).
        - *Review* (the whole diff against the Code craft rubric): the step review's focus already held the rubric
          and the same checklist.
        - *Assembly* (chained work on the ask-agent route): a bullet of the item review's steps wording, "two steps
          that conflict, or disagree at an interface they share".
        - *Later checks*: document's open items, due at the stage that makes the check.
        - *Reconcile cases*: the test stage's ID, floor and RED gates at every step, so nothing is left to reconcile by
          hand. *Services* got no new home: in the five runs verify found no service issue (§7.2); test-spec plans
          service cases.
      - **The item commit.** `_item_commit` is gone. On the inline route each step's commit stage commits it; on the
        ask-agent route `_item_commit_stage` commits the item whole as `feat: <item> <title>` when its document stage
        and review are accepted, fail-closed like the step's. Both name the changed files they leave
        (`_left_notice`), and document's packet prints "Changed, ShipLoop will not commit: …" when one is left.
      - **Removed with verify.** The change inventory (lint), the advisory lint pass at its entry, `shiploop_quality`
        and its rubric file, verify's one-trivial-review loop (`TRIVIAL_REVIEWS`, `_LOOP_LAST`), its RED-unobserved
        lines (product-acceptance keeps every item's). Carry-forward reads the item's test and document results, and
        its unnamed-commands line reads the item's test stage (`_passed_commands`).
      - **Run Review** reads the new loop as stage model v6, and an 8-stage run with verify as v5, frozen as v4 is
        (`defaults/stages-v5.json`). Per-step rendering stays 2b-5's.
      - **A defect from 2b-2, found here.** The step review's handoff still told the child to commit, though its focus
        said "Leave your edits uncommitted". It did so in its Commit section (improve-commit and its message rules),
        its top line, Checked-by, Changes and Evidence lines. A review that followed it would have moved HEAD inside
        the step, and since 2b-4a the commit stage refuses that.
        - Now every one of those lines says the step review commits nothing (`STEP_REVIEW_COMMIT_LINE`), and
          `improve-commit` refuses at a step review, naming improve-pass. improve-pass already left the edits
          uncommitted (`STEP_REVIEW_NO_COMMIT`, 2b-2).
        - The handoff fits pilot A again (21,475 bytes inline, 21,896 on the ask-agent route). Its Commit line ends at
          5,395 and 5,476 characters, inside a 5,600 window that improve-route measures; every other review keeps
          4,500.
      - **Suites that `--changed-from` never selected had drifted since 2b-2.** improve-route, improve-schedule,
        consumer-delivery, send-back and chain still expected implement's step review, or a walk from S1's build
        straight to S2's. Each failure was checked against 3e4c3e0e or 388de0bf. The whole shiploop group now runs
        for this switch, and it ran on the commit (Evidence below).
      - **Left for 2b-5** (E2E audit harness): `test/shiploop_e2e/counters.py` matches only `feat: <item> ` subjects,
        so it counts no inline step commit (`feat(W1/S1): …`); `slice.py`'s docstring still names verify. Recorded
        fixtures and evaluators that name verify are history and stay as recorded.
      - **Evidence.** `run-all.sh --group quick --group shiploop --changed-from fdad45b4`: 118 suites in 1,776 s; 116
        passed. The two that failed, delegation and packet-completeness, still expected the improve-commit command in
        the step review's handoff; both pass after the fix (66 and 63 tests). Fail-first tests, each seen failing
        first:
        - the version-9 refusal (send-back);
        - the v5/v6 stage models (run-review StageModelTests);
        - the step review's Commit section (improve-route);
        - improve-commit refused at a step review (actual-improve-cli, through the real CLI);
        - 2b-4b's three gate tests (below).
    - **2b-4b, 2026-10-28: verify's gates move into the step.**
      - **Document's done** runs the lint gate and a rerun, both measured from the tree document began from. That tree
        is recorded at its entry as `entry`, by `_document_entry` (read back by `_stage_base`).
        - The lint gate judges only document's own lines. A finding implement or test waived is not document's to
          waive again, and the refusal says "on lines the document stage changed".
        - The rerun (`_document_rerun`) covers what document's edits could affect, out of the commands its step's
          test stage ran:
          - nothing after no edit;
          - the check commands after edits to no code or test path, so a docs edit reruns the doc checks;
          - every command after a code or test edit, or when the edits cannot be read.

          So a step whose document edits only Markdown does not rerun its test suites (the owner's 2d cost rule). The
          design's §8.2 table said exactly this: "lint on docs; the doc checks among the recorded commands".
      - **The step review's import** lints the lines the review changed since its bind snapshot
        (`_review_lint_gate`), then reruns the step's commands as before. Since 2b-2 the review's edits to every step
        but the last were linted by no gate: verify's gate measured from the last step's base.
      - **Refused reruns.** Document's refused rerun opens its send-back route as verify's does (`loops._rerun_refused`).
      - **Evidence.** Fail-first tests, each seen failing first:
        - shiploop-test-loop `test_document_reruns_what_its_own_edits_could_affect` (all three cases);
        - shiploop-lint `GateTests.test_document_is_gated_on_the_lines_it_changed_and_only_on_them` and
          `test_a_step_reviews_edits_are_gated_at_its_import_on_the_lines_the_review_changed`.
    - **2b-4a, done 2026-10-28.** The step's commit is the iteration's commit stage (`_commit_stage`, which replaces
      `_step_commit`).
      - **When it runs.** It runs in the call that accepts the step's last stage: document's complete, or the import
        of its review. Nothing writes the checkout between those gates and the commit, so it commits the tree the
        gates ran on, by construction.
        - So `commit_decision` lost its two tree arguments and `Decision.reopen`. They could never differ in that
          call, and a test run that writes output would have made a later comparison refuse every retry.
      - **Fail-closed.** Before, a commit Git refused printed a note and the step moved on uncommitted, left for
        verify's item commit. Now the call is refused and nothing is saved, so the step advances only once its commit
        lands. The same callback, run again, retries it; at an import that reruns the review's gates as well.
        A step whose changes cannot be read (no base was captured, as a harness seed can leave it) is skipped with a
        note, as the base run and the mutation check are, because no retry could read them
        (`shiploop-e2e-slice`'s seeded-without-base drive caught the first cut, which refused it).
      - **Pending record.**
        - The step's ledger row (`RUN/iterations/<item>.json`) holds `pending`: the iteration, its parent and the
          planned tree (`shiploop_git.planned_tree`, HEAD plus the scope paths, built in a temporary index). It is
          written before the commit and dropped once the commit is recorded, or when the step is entered again.
        - A call that stopped after Git committed is recognised on retry (`done`), not committed twice.
        - A HEAD that anything else moved inside the step is refused. The refusal names `git reset --soft <base>`,
          which keeps the changes, or blocked when the commit is not the step's work.
      - **Already true before 2b-4a.** Inside an iteration the review leaves its edits uncommitted
        (`STEP_REVIEW_NO_COMMIT`), and the knowledge close skips implement and test. Git runs without hooks
        (`shiploop_git.git`), so a refused commit means a lock, a permission or a disk failure, never a product hook.
      - **Not in 2b-4a.** Verify's item commit still runs on the ask-agent route, and on the inline route after the
        last step, where it finds nothing left to commit.
      - **Evidence.** Fail-first tests, each seen failing before the code:
        - shiploop-navigator-contract: a held index lock refuses the review's import, with nothing saved, and the
          same import then commits once; a commit that landed before ShipLoop recorded it is recognised; a
          hand-made commit inside the step is refused, and committed once reset;
        - shiploop-actual-improve-cli: the same refusal and retry through the real `complete` CLI on an Improve
          stage. With HEAD's navigator it was accepted and moved to verify.
        - shiploop-iteration's commit tests were updated for the new signature.
        - The quick tier (`run-all.sh --group quick --changed-from 1e192981`, 71 suites, 612 s) failed only that
          slice test; after the fix, shiploop-e2e-slice (60) and the navigator's EightStageInnerLoopCliTests (22)
          pass.
  - **2b-5. The rest of the switch.**
    - The packets' text, Run Review v6 and the E2E audit harness.
    - The lifecycle's change note (`bump: minor`).
    - **The packets, done 2026-10-28.**
      - **Skills per stage (F9, §8.2c).** A step plan's skill entry takes an optional `stages` list (implement, test,
        document, improve; implement when absent), refused when it names any other stage
        (`expectations.normalise_skills`).
        - Implement's Step block lists implement's skills.
        - The test and document packets print the step just built and "Skills for this stage". Before, the test packet
          had no Step block at all, which 2b-2 had left open.
        - The step review's handoff prints "Skills for this review".
        - Each line names the skill's use and locator, or says none is listed and points at KNOWLEDGE/environment.md
          `## Skills` (`step_skills`, `_skills_line`, `_review_skills_lines`).
        - The test duty now says to use each skill its packet lists, and still assumes no unlisted skill or MCP.
        - Not built: a skill a later item's carry-forward created reaches a step only through environment.md
          `## Skills` and the step plan, which rereads the index; there is no knowledge stage to create one mid-item
          (2b-3, option C).
      - **Lint's wording.** A lint record says "on a line changed since the base" in place of "this item changed".
        Since 2b-2 every gate measures from its own base (the step's, document's entry, the review's bind), and the
        record's Base line names which. An inline step's refusal says "on lines this step changed".
      - **Size.** step-plan's duty text gained the `stages` field: its head is 19,995 characters inline (+51) and
        19,536 on the ask-agent route. The first cut was 137 characters longer and pushed the layers-at-their-limit
        step-plan head past the cut, which dropped its References block; shiploop-step-packets caught it. The test
        head is 17,954 on both routes (+54).
      - **Evidence.** Fail-first tests:
        - shiploop-test-loop `test_each_stage_of_a_step_lists_the_skills_the_step_plan_names_for_it` and
          `test_a_step_skill_naming_an_unknown_stage_is_refused`;
        - shiploop-lint's seven wording assertions.

        Head pins are in test/shiploop_e2e/head_table.json; head-order allows test's Step block at P0.
    - **Run Review per step, done 2026-10-28.** A v6 run's inner visits carry their step (`stages[].step` on implement,
      test and document, with the step just built at test and document, as the engine reads it). Each work item's
      `steps` list gives each step's number, its visit range and its commit.
      - The commit is read from the iterations ledger only: absent when unknown, `null` when the ledger records none.
        The exporter reads no git log.
      - The page groups the visits under one header per step: "Step S1 · implement → test → document → review · commit
        1a2b3c4". The review is the document visit's Improve child; the engine records no history row for it.
      - A send-back restarts the numbering under the new plan. v4 and v5 runs render as before.
      - Fixed on the way: an item stopped between steps counted as past implement and lost its `stepsExecuted`.
      - Nine fail-first tests: shiploop-run-review StepIterationExportTests and StepGroupPageTests.
    - **The E2E audit harness, done 2026-10-28.**
      - **Step commits were miscounted.** `test/shiploop_e2e/counters.py` counted every inline step commit as the
        model's (`other`). They are ShipLoop's: the commit stage's, and before 2b-4a the step commit's.
        - A read-only regrade of the 108 runs under ~/e2e-runs found 97 step commits in 30 runs from 2026-10-20 on, all
          counted as the model's. In 26 of those runs `other` was exactly the step-commit count. For example:
          - chess-sf-full-12a23d: script 21 -> 32, other 11 -> 0;
          - ds-flash-978478-battleship: 21 -> 33, other 12 -> 0;
          - gate-2100 battleship: 14 -> 16, other 3 -> 1, a real model commit.
        - A step commit is now ShipLoop's by its announcement ("ShipLoop committed step W1/S1 as …") or by its
          `feat(<item>/…` subject for an item of the run. A `feat(ui)` commit, or one naming another run's item, stays
          the model's. The committed fixtures are unchanged.
      - **Verify-era text.** The harness text that presented verify as live is updated: `slice.py`, the harness
        README, SPEC.md's gate list and comments in `run.py` and metrics. `metrics.skipped_gates` and `flow.py` read
        the item-commit gate at an accepted document; for older runs, at verify.
      - **Kept as recorded.** LEARNINGS.md entries, the `tests/*-verify<N>.md` record names, `packet_anatomy.py`'s
        grouping of 8-stage runs, and `behavior_capture.py`'s stage allowlist, which keeps verify so that older
        captures still parse.
      - **Evidence.** Five fail-first tests in shiploop-e2e-commit-counters and shiploop-e2e-efficiency.
        - `ClassifyTest`: script/other is (7, 5) with the run's ledger, against (5, 7) before.
        - `ShipLoopOwnedSubjectsTest` pins `step_commit_message` and the announcement line.
- **Step 4 (lane D), the edge cases, 2026-10-28.** The cases are driven through the real `complete` in a new suite,
  `test/shiploop-step-edges.test.py`. Commit failure and retry were done in 2b-4a. Tests a review adds are step 3's,
  in lane B.
  - **A defect, since 2b-2.** At every step after the first, the base run refused an earlier step's focused IDs:
    they pass on the later step's base, as they should, and the RED check judged them as new. `red_na` could not exempt
    them, since it accepts only `new_ids`. So a multi-step item with code was stuck at its second step's test stage.
    (An item whose validate-existing made a preparatory fix was not: see "Not fixed here" below.) The plain walks never
    showed it, because they used docs-only or one-step plans.
    - Fixed in `test_loop._base_run`. It judges only the step's new cases (`new_ids`), runs and counts the rest, and
      records them as `earlier_steps` in the base record. A focused command holding only earlier steps' cases, with IDs
      or with only criteria, is counted, not judged (`iteration.earlier_command`, `test_loop._earlier_step`): an
      ID-less command exits 0 on that base too.
    - Fail-first: before the fix, the cross-step test was refused at S2 with "passed TC-1 on the item's base". With the
      base run's RED switched off for the step's new cases, the retention test fails ("NavigatorError not raised").
  - **Covered now:**
    - A send-back after S1 is committed commits nothing and keeps S1's commit. The next plan's S1, with nothing left to
      change, starts no review and makes no commit. Its S2 is committed on S1's commit, and the ledger keeps both
      plans' rows.
    - A step review whose result is a send-back commits nothing. The step's change stays in the checkout, and the next
      plan's S1 commits it.
    - A case whose criterion S1 and S2 both list is due at S2 only. S1's test stage passes the real gate before that
      case's test exists, and S2's is refused until it runs.
    - RED holds at S2 for the cases new there: S1's change already holds what TC-2 asserts, so TC-2 is refused by
      name while S1's TC-1, which passes there too, is not judged; `red_na` takes TC-2.
    - **After a send-back the redone plan counts steps afresh**, so a case an earlier plan's S1 committed is new again at
      the redone S1 and passes on that base. The base run refuses it and the refusal names the way through: `red_na`,
      worded "a case a step committed before a send-back". The cost is one avoidable refused run per such case;
      red-check shows it first (not counted).
    - `red_na` names only a test ID new at this step, and `retired_tests` refuses an ID a focused command still lists,
      an earlier step's included. Both refusals now say so. The base rule in the packet says "No test ID new at this
      step may pass there" and that an earlier step's IDs "are not judged".
    - A step that only changes test files is still refused (owner sizing rule), now saying the test stage writes the
      tests for the behaviour the steps build (route-neutral: the ask-agent route has one test stage for every step).
      The old text said the test stage runs "after the last implement step", untrue on the inline route since 2b-2.
  - **Adversarial review.** 37 agents read the diff through three lenses (RED correctness, suite validity, words
    against behaviour) and two skeptics tried to refute each finding: 17 findings, 13 survived, all fixed above except
    the one below. They also found that the first version of the suite did not pin RED at later steps; the
    retention test does.
  - **Not fixed here (lane B, step 3).** With a preparatory-fix commit, every step's base run and mutation check take
    the tree before step 1 (`_test_loop_gate` passes `base_commit=preparatory_base` at every step), so RED is weaker
    there: a step's new test that asserts only an earlier step's behaviour fails there and is accepted. Step 3's
    "shared baselines" build (the preparatory commit moves the base only at the first step) is that fix. When it merges,
    `iteration.earlier_command` must also be checked against lane B's folded row (a focused row that is also the minimum
    regression, run alone with no IDs at an early step).
- **2c. The ask-agent route** gets the same step boundaries (G1).
- **2d. Test gradations** (owner to-do, 2026-10-28). The owner, in full:

  > "One of the things that I want to make sure of in our test suite is that we're both running the tests for the new
  > code and a sufficient amount of regression tests. Again, we got to be careful because we really need test suites.
  > Some are going to be really long and time-consuming. We don't need to run full regressions on everything, so we
  > kind of want gradations of test suites to be run: to make sure the new code didn't break existing things, as well
  > as the fact that the new code is actually validated to some degree.
  >
  > We need some finesse in the test stage that has an appropriate prompt that determines whether this is a new test
  > suite, whether it enhances the minimum test suite, or whether it can always add tests to all of the suites as
  > needed. We want to make sure that the code didn't break anything basic, and then also that the code is implemented
  > in detail and tested in detail in the testing phase for the code that was just added. That one we want to run in
  > full mode, if you will. We definitely want to make sure that we don't do exhaustive regressions on every iteration
  > because that would be extremely expensive. Again, we should really consider unit tests and mock tests as much as
  > needed to validate a lot of the code and the logic that we needed. We should not be afraid to use MCP servers,
  > skills, or anything of that nature if needed to test the newly added code in detail."

  What it changes:
  - **Each step runs three tiers.**
    - **Full detail on the new code:** the step's focused cases, unit and mock tests first.
    - **The earlier steps' focused tests:** they carry over, as 2a already projects them.
    - **A minimum regression,** a fast suite that shows nothing basic broke.
  - **The exhaustive regression** runs at the item's last step, never on every iteration.
  - **The step plan marks the tier.** A regression command marked `minimum` runs at every step, and an unmarked one
    only at the last. A plan of two or more steps records a minimum command, or a reason it has none.
  - **The test packet asks where each new test belongs:** a new suite, the minimum suite, or the full suites.
  - **It names the tools.** MCP servers and skills may be used to test the new code in detail, beside the unit and
    mock tests.
- **F6. Lint coverage shown, done 2026-10-28** (the owner's go on §8.5's recommended form).
  - **What landed.**
    - A lint pass prints `Lint coverage:` on the line after its `Result:` line (`shiploop_lint._coverage_line`,
      stored as the record's `coverage_line`). It counts the files a linter covered and names the linters, then
      lists every other changed file with its coverage text, grouped:
      - *syntax only, not linted*: `node --check`, a JSON parse, or a linter that was unavailable or timed out;
      - *not linted*: no catalogued linter, excluded, or not in scope;
      - *linted in part*: another linter the repository configures did not run, timed out or failed.

      Deleted files are left out.
    - On 36036c's shape the line reads: "1 file linted by ruff; syntax only, not linted: game.js, server.js (syntax
      checked by node --check (no catalogued linter)); not linted: public/index.html (not in scope: no catalogued
      linter for this file type; git diff --check only)".
    - **Where the model sees it.** The packet's lint digest (`render_lines`, `_packet_digest`) keeps it beside the
      verdict, though it still leaves the per-file Coverage section to the record (U13). Both gate refusals (after an
      auto-fix, and on an unwaived finding) print it, and so does a pass that could not run (`NONE_COVERAGE`).
      `shiploop lint --action` prints it with the block.
    - **Lint off.** Implement, test and document print `OFF_COVERAGE` in their lint-commands block
      (`lint.command_lines`): no linter and no lint gate run, so the step chooses its own static checks. Before, an
      off run printed nothing there, though `_lint_command_lines`' docstring said it did.
  - **Packet size.** The offline walk runs with lint off, so those three stages grow by the off line, 176 characters
    with its newline, head and whole on both routes (`test/shiploop_e2e/head_table.json`): for example inline test
    head 17,954 -> 18,130 and whole 19,852 -> 20,028. Every head fits the 20,000 cut. The bound rose rather than the
    line being cut, since it carries an obligation.
  - **Evidence.** Four fail-first tests in shiploop-lint `CoverageLineTests`, each seen failing before the code (no
    `coverage_line` key, no off line, refusals without the line): the result's coverage line and the digest that
    keeps it; a tool unavailable, timed out, and a configured linter not run; both refusals and a pass that could not
    run; the off line at each gate stage and its absence elsewhere. shiploop-lint passes (105 tests), and so do
    shiploop-packet-recut and shiploop-step-packets with the new pins.
  - **Kept out.**
    - The run's report. Its achievement report reads no lint record, so the line would need a new reader (§8.2a
      named it).
    - The environment.md coverage line (8.2b). That belonged to option A's knowledge stage; under option C document
      reflects, and a reviewer reads the coverage in the step's lint records.
    - A gate on coverage. A syntax-only or unlinted file still never refuses: the line informs, as §8.5 recommends.

**9.2 New decisions:**
- **G1. The ask-agent route.** Recommended: the same step boundaries, so one lifecycle. The alternative keeps it
  item-level, which is a second lifecycle to maintain.
- **G2. Framing.** Recommended: present §8 as a quality and feedback-speed pilot. Its cost is measured, not forecast.

Still unproven (Astra's open unknowns):
- the net cost;
- how faithful the mocks are;
- whether the relocated review and the entry-point tests catch what verify used to catch.

The pilots decide these.

## Not in this design

- Improve's pass loop and its stop rule.
- The planning and end-of-work reviews (D4).
- Mutation-checking the tests a review adds.
