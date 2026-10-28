# Improve review after the item's tests pass (design T), 2026-10-27

Status: **design only; nothing built.** **§8 (2026-10-27) is the current proposal:** the owner's per-step iteration (build, test, document, Improve, commit for each step in turn). It supersedes the item-level order of §1 and §4 and the item-level flow of §7, and keeps their gates and evidence. §7 (2026-10-27) adds the gated flow: verify's checks become tests and gates,
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
    the test stage) names three tests that ran.
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
- asked that the test stage build mocks that simulate the expected behaviour before the system tests.

8.2, 8.2a and 8.3 say what changed.

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
- Earlier (memory `todo-step-series-order`, 2026-10-17): each planned step runs its own series, in plan order.

**8.1 The shape.**

| when | stages | who works |
|---|---|---|
| once per item, before the steps | step-plan; test-spec, which specifies every case (its ID, oracle, RED and GREEN) and assigns each to a step; validate-existing | model |
| **for each step, in plan order** | **build → test → document → Improve → commit** | model, except commit: ShipLoop only |
| once per item, after the last step | carry-forward | model |

- Verify is retired. The commit stage replaces it and is named for what it does.
- The commit stage follows Improve, the iteration's last edit. It is still the commit "on every iteration right after
  the documentation": the documented and reviewed step goes into one commit.
- The next step's build starts from that commit.

**8.2 Each stage and its exit gates** (all run by ShipLoop; a refusal returns to the same stage):

| stage | the work | exit gates |
|---|---|---|
| build | write this step's code | **lint the production code** (8.2a); the step's Proof |
| test: build out the test specification | build mocks that simulate what the step's dependencies are expected to do; turn each test-spec case assigned to this step into a test against them, titled with its ID and asserting the case's oracle (never the code's current behaviour); add a valid, a boundary and an invalid case for each entry point the step changed; lint the test code; perform them by running every recorded command; loop: fix the code, or a test for a recorded independent reason, until one run after the last edit passes every gate | **lint the test code and any production code the loop changed** (8.2a); the tests pass; IDs; floors; RED against the code before this step; mutation of this step's changed lines; the entry-point map |
| document | update the docs this step's change affects, from the behaviour the tests now show | lint on docs; the doc checks among the recorded commands |
| Improve | review the whole step together (code, tests and docs), now green and documented. A behaviour fix adds a test for it and corrects the docs it affects; a doc that disagrees with the code is a finding. Rerun every command after each edit | its own rule (a pass that changes nothing material ends it); at import, the iteration's final gate: lint and a rerun of every recorded command, doc checks included |
| commit | ShipLoop commits everything the iteration changed (code, tests, docs, review fixes) as one `feat(<item>/<step>)` commit. Its message carries the step's learnings and decisions, the review's lessons and the evidence. | none of its own: it checks that the tree is the one Improve's final gate ran on |

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
  (`shiploop_mutation.mutation_check`). It is the check that the tests would catch a bug. It refused at least once in
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

## Not in this design

- Improve's pass loop and its stop rule.
- The planning and end-of-work reviews (D4).
- Mutation-checking the tests a review adds.
