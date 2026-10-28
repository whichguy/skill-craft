# Item width from measured step changes (design C), 2026-10-27

Status: **design only; nothing built.** [Design T](shiploop-review-after-tests-design-2026-10-27.md) (2026-10-27) moves these reviews after the item's test stage; with T, they wait at the test stage's done instead of the last step (T §4, point 7). The owner's request: "Design the wide-item rule on measured step changes:
ShipLoop carries each step's changed files forward and the item's end decides one review or one per group. Ground it
in the runs, build nothing yet."

If built, C replaces two parts of B ([the wide-item design](shiploop-wide-item-review-design-2026-10-27.md), released
in 2.18.0): how B tells a wide item (the step plan's declared `steps[].paths`) and when it reviews one (after each
step). F1, the proposal that the step plan must declare each step's paths, is dropped: nothing has to be predicted.

Consumer: first the owner, deciding D1 to D4 (§6), then the session that builds C.

**Why.** B reads the paths the plan declares for each step. Sonnet's 2.18.0 plan (v2180-sonnet-battleship-36036c)
declared none, so its three steps formed one group, and B behaved like P0's one item review
(`test/shiploop_e2e/LEARNINGS.md`, "Wide-item rule (B) live check"). A plan can leave paths out, or name the wrong
ones. What each step actually changed is already measured by ShipLoop (§1).

**Evidence.** Every run under `~/e2e-runs/2026102*/` that kept its delivered history (`delivery/work.bundle`): 9 runs,
11 work items with a changed step. The tables are in
[`docs/experiments/e2e-measured-width-20261027/`](experiments/e2e-measured-width-20261027/):
- `step-changes.txt`: each step's committed files, and the groups the steps form under four joining rules;
- `step_changes.py`: the script that made it.

The review outcomes cited come from the B design's §1 and from the 2.18.0 run's `probes.md`.

## 1. What ShipLoop already measures

- **Step snapshots.** ShipLoop snapshots the working tree, untracked files included (`improve_changes.snapshot_tree`):
  - when an inline step starts (`_step_entry`, the action's `base`);
  - when it ends (`_step_after`, the action's `after`).

  P0's no-change skip (P4) already compares the two.
- **Step commits.** `_step_commit` commits each accepted inline step as `feat(<item>/<step>): …` (build plan S3.2).
  It records the commit at `commits/<action>.txt`.
- **What is missing.** The action record holds only the current step. An earlier step leaves only two things behind:
  - `item_base`, the tree when the round's first step began;
  - `round_changed`, whether any earlier step changed a file.

  The list of files each earlier step changed is not kept.
- **Snapshots, not commits, are the design's source.** A step commit has two gaps:
  - it takes only the commit scope (declared paths and documentation, `item_scope.commit_scope`);
  - it records nothing when the commit fails.

  The snapshots cover every changed file. In the recorded runs the two agree: no step commit failed, and no verify
  printed its left-out notice. So the evidence below reads the step commits, and C reads the snapshots.
- **Side finding.** `_step_entry`'s docstring says an item's earlier steps "stay uncommitted until verify". Since S3.2
  they are committed. The build corrects the wording.

## 2. What the runs' steps changed

From `step-changes.txt`. A step that changed no file made no commit, so it is not listed.

| run, item | steps that changed files | files, step by step | B: declared groups | C: measured groups |
|---|---|---|---|---|
| Sonnet 36036c W1 | 3 | `game.js` / `server.js` / `public/index.html` | 1 (no step declared paths) | **3** |
| Sonnet 01b9b3 W1 | 3 | `game.js` / `index.html` / `server.js` | 3 | 3 |
| Sonnet 491d9a W1 | 3 | `game.js` / `server.js` / `server.js` | 2 | 2 |
| DeepSeek 978478 W1 | 4 | `lib/game.js` in each | 1 | 1 |
| DeepSeek 978478 W2 | 6 | `server.js` + `public/index.html` / `server.js` ×3 / `README.md` / `test-support/server.js` + `test-assets/…` | 3 | 2: `README.md` joins S4's group |
| DeepSeek 978478 W3 | 2 | `public/index.html` / `e2e/chrome.js` + `public/index.html` | 1 | 1 |
| DeepSeek 759a03 W1 | 3 | `battleship.js` (+ `.gitignore` in S1) in each | 1 | 1 |
| DeepSeek 759a03 W2 | 3 | `server.js` + `public/index.html` ×2 / `server.js` | 1 | 1 |
| DeepSeek 759a03 W3 | 1 of 3 | `browser-check/cdp.js` + `docs/shiploop/environment.md`; S2 and S3 changed nothing | 2 | 1 |
| Ollama hello 993a9d W1 | 2 | `hello.py` / `.gitignore` | 1 | 1: `.gitignore` joins S1 |
| the one-step items | 1 | — | 1 | 1 |

- **Measured and declared groups agree on every item whose steps declared paths, with two exceptions:**
  - 759a03 W3 declared two steps that then changed nothing;
  - 978478 W2's `README.md` step was its own group under B, and joins S4's group under C's rule (§3).
- **36036c is the item B missed.** Measured, its steps made three groups, the same three files as 01b9b3's per-step
  baseline.
- **No step commit held a test file.** In these runs the tests came from the test stages, not from implement steps.
  So a shared test helper never joined two steps here, but the rule still has to handle one.
- **Non-code files did appear in step commits:**
  - `.gitignore`, twice;
  - `README.md`, once;
  - `docs/shiploop/environment.md`, ShipLoop's knowledge home that any step may add to, once.

  Joining steps on any shared file would join them through files like these.

## 3. The design (C)

Rule `item` keeps its name (one term per concept). Its schedule goes back to P0's: there are no reviews between
steps, and every implement review starts at the item's last step. What that point decides changes.

**1. Measure each step.**
- At `_step_after`, record the step's changed paths on its action as `changed`. This is the diff between its `base`
  and `after` trees, with ShipLoop runtime paths dropped, as `item_scope.changed_since` drops them.
- `_step_entry` carries the round's list forward to the next step's action as
  `round_steps: [{"action", "step", "changed"}]`.
- The list replaces `round_changed`, which becomes "any entry's `changed` is non-empty". One supported version:
  `round_changed` goes.
- `validate`'s key rule for an implement action changes with it.

**2. Group the steps.** A pure helper in `shiploop_loops` replaces `step_path_groups`. It works over the round's steps
that changed a file:
- Two steps join when they changed a common **code** file. Code is the path catalog's default class:
  `item_scope.classify` returns `code` for anything that is not test, docs, config or metadata.
- A step that changed no code file joins the group of the step before it. If it is the first step, it joins the next
  step's group.
- Each group's files are every file its steps changed, whatever their class.

**3. Decide at the item's last step.**

| measured at the last step | reviews |
|---|---|
| no step of the round changed a file | none (P4, as now) |
| some step's change is unknown (outside Git, or its snapshot failed) | one item review, as now; its base line already says "not recorded" |
| one group | one item review, as now (P0) |
| k groups | k reviews, one per group, in the order of each group's last step |

**4. Run one review per group.**
- **Each group's review is the Improve stage of that group's last step.** For example:
  - in 36036c, `{S1}` is reviewed as S1's stage, `{S2}` as S2's, `{S3}` as S3's;
  - in 491d9a, `{S1}` as S1's and `{S2, S3}` as S3's.
- **Nothing is renamed.** This is how B and the schedule before P0 keyed their step reviews. So these all keep their
  current keys: the binding ID (`run/<action>`), the child directory (`implement-<last 8>`), the bind, inbox and
  result files, and `improve_results`. No two reviews share an action.
- **The order.** The cursor stays at the item's last step with that step's result parked. The earlier groups' reviews
  run first. The last group's review is the last step's own: it finishes as today and applies the parked result.
- **The state change.**
  - `active_improve` may name an already-accepted step of the current round, but only while the cursor waits at the
    item's last step.
  - The groups still to review are queued in the cursor's action record.
  - `validate` relaxes its rule that the child's action is the current one, in that case only. Its binding-identity
    check then compares against the child's own action.
  - `finish_improve`, for an earlier group, records that step's `improve_results` entry and starts the next group's
    child, instead of applying a result.
- **An earlier group's step result is already accepted.** Its review's fixes are its own commits, as every review's
  are. Its `complete` submits the step's result unchanged; a revised one is refused, and the refusal names that exit.
  Following the route-testing rule, a test submits that exit through the real gate.

**5. The group review's handoff** is the item handoff restricted to the group:
- the group's Accepted step lines, and its last step's result by value;
- the review base: `git -C <repo> diff <item_base> <bound> -- <the group's files>`;
- the position, for example "review 2 of 3: S2 (`server.js`)".

The rerun line stays "the item's test stage, after its last step, runs over it".

**6. Unchanged:**
- the ask-agent route, whose one action builds every step and gets one review;
- the planning reviews, and the end-of-work review after the last item's carry-forward;
- the Improve skill and its pass loop.

**Where it lands:**
- `shiploop_navigator`:
  - `_step_after` and `_step_entry` (measure and carry; their docstrings);
  - `_improve_checkpoint` (rule `item` at the last step only; B's per-step branch and `_wide_item` go);
  - `apply`, `finish_improve` and `validate` (the queue);
  - `_item_steps`, `_review_base_line` and `_item_review_lines` (the group handoff).
- `shiploop_loops`: the grouping helper, which replaces `step_path_groups`.
- The words:
  - the glossary's "Improve stage" and "wide item" rows (wide: two or more measured groups);
  - the `IMPROVE_RULES` comment in `shiploop_stage_spec`;
  - the common prompt's "(each changed step when the item's steps work on separate paths)", which becomes one
    review per group of steps that changed separate code files;
  - `navigator.md` and `improve-stages.md`;
  - the Run Review stage catalog's implement check text.
- Change notes:
  - `changes/shiploop/measured-item-width.md`, `bump: minor`, because it changes the review schedule. It says that
    it replaces B's declared-path rule;
  - a patch note for shiploop-run-review.

**Tests.** Fail-first, through the real CLI, in `test/shiploop-navigator-contract.test.py`:
1. **36036c's shape.** Three steps that declare no paths, each changing its own file. Three Improve children start
   after S3, as S1's, S2's and S3's stages, in that order. Each base line is restricted to that step's file.
2. **491d9a's shape.** `game.js` / `server.js` / `server.js` gives two children, S1's and S3's. S3's review names S2
   and S3.
3. **One group, unchanged.** Three steps on one file give one child, after S3. This is the existing P0 test; its
   fixture's steps then have to change one file, whatever paths they declare.
4. **A non-code step joins.** `hello.py` / `.gitignore` gives one child.
5. **Unknown change.** A step without snapshots gives one item review.
6. **The refusal route.** An earlier group's `complete` with a revised result is refused, and the named exit is
   accepted.
7. **The helper.** Unit tests in `test/shiploop-loops.test.py`, pinned on the measured rows of §2.

B's tests that assert reviews between steps (`test_a_wide_item_starts_an_improve_stage_after_each_step…`,
`test_a_wide_items_step_that_changed_no_file…`) are rewritten to C's end-of-item shape, not kept beside it. Then run
the quick tier with `--changed-from`. Also run the suites that pin packet counts (`SMALL_HOME_FINGERPRINTS`, and
e2e-efficiency's packets and handoffs), and re-pin any count C moves, giving the reason.

## 4. Against the evidence

**Reviews per plan** (per step before P0 counts every step, as in the B design's table):

| plan | per step (before P0) | P0 | B (declared) | C (measured) |
|---|---|---|---|---|
| Sonnet 01b9b3 | 3 | 1 | 3 | 3 |
| Sonnet 491d9a | 3 | 1 | 3 | 2 |
| Sonnet 36036c | 3 | 1 | 1 | 3 |
| DeepSeek 978478 | 12 | 3 | 8 | 4: W2 gets 2, not 6 |
| DeepSeek 759a03 | 9 | 3 | 3 | 3 |

**Where the catches were** (B design §1.1, and 36036c's probes):
- **01b9b3.** The three catches came from the reviews of S1 (`game.js`), S2 (`index.html`) and S3 (`server.js`).
  Under C each is its own group, so C keeps all three reviews and moves them to the item's end.
  - Groups share no code file, so no later step changed a group's code.
  - A group's review therefore reads that code as its own steps left it, with the later steps' callers present.
- **36036c.** C gives the page its own review: the review the stale fire reply needed and the item review missed.
  `GET //`, which the item review already fixed, sits in the `server.js` group.
- **491d9a: where C is weaker than B.** Its `server.js` group holds S2 (the routes and the store) and S3 (the inline
  page), and all three misses were in it. C reviews them once; B reviewed them twice.
  - This is the case the B design rejected B′ for.
  - Measuring by file cannot split one file into components.
  - The premise that made it decisive, one finding pass per Sonnet review, is now superseded: 5 of 8 stages in 36036c
    made two. So this is an open measurement, not a known loss.
- **DeepSeek.** Its narrow items keep their one review each: all of 759a03, and 978478's W1 and W3. That keeps the
  item reviews that fixed 9 defects in 10.4 minutes. 978478's wide W2 gets 2 reviews, against B's 6.

**What moves with the timing.** Under C, reviews run at the item's end, not after each step. Later steps are built on
code nobody has reviewed yet. A group review's fix that changes something another group calls must keep that caller
working, and the item's test stage, which runs after the reviews, is what catches it if not. A send-back to
implement is what that cost looks like, and §5 watches for it.

## 5. How to tell it worked, after the build

| run | must hold | should improve | watch |
|---|---|---|---|
| Sonnet battleship (`--backend anthropic`) | PASS; no send-back to implement | when an item measures two or more groups, the probes find `GET //` and the stale fire reply fixed on the shipped product (`probes.md`) | Improve awake minutes, against 9.4 (01b9b3), 8.7 (491d9a) and 10.3 (36036c) |
| DeepSeek battleship | PASS; no send-back to implement | Improve minutes within 10% of 759a03's 62.7 when its items measure one group | each item's group count, and what the extra reviews cost |

- The report prints each item's measured groups. A run whose items all measured one group did not exercise C, and the
  report says so.
- The results are n = 1 per model. A regression is rerun before it decides anything.

## 6. Decisions for the owner

- **D1. What joins two steps.** Recommended: a shared code file, with a non-code step joining the step before it.
  - Joining on any shared file would join steps through `.gitignore`, `README.md` and the knowledge home (§2).
  - Code and test together equals code alone on these runs, since no step changed a test. On other plans it would
    join steps through a shared test helper.
- **D2. One review per group, or per changed step of a wide item.** Recommended: per group, as the request words it.
  It is cheaper on DeepSeek (978478 W2: 2, not 6). Per step gives 491d9a three reviews, as B did, and keeps B's
  count at the item's end.
- **D3. How several reviews run at one point.** Recommended: each group's review is its last step's Improve stage
  (§3, point 4), which keeps every file key. The alternative runs several reviews under the last step. That needs a
  new key in the binding (`standalone_improve`'s action check), the child directory, the bind, inbox and result
  files, `improve_results`, the trace, the Run Review export and the e2e-audit harness.
- **D4. B goes when C lands** (one supported version), and F1 is dropped. Recommended: yes.

## Not in this design

- Splitting one file into components (491d9a's `server.js`).
- A manifest class in the path catalog. A shared `package.json` counts as code and would join steps. No recorded
  step changed one, and the catalog stays free of stack-specific rules.
- The ask-agent route, and Improve's pass loop.
