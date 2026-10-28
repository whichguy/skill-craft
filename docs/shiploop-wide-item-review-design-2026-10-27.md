# Wide work items keep per-step Improve reviews — design, 2026-10-27

Status: **B released in 2.18.0 (292a2a36); its first live run did not exercise it** (2026-10-27, v2180-sonnet-battleship-36036c:
no step declared paths, so the item formed one group; see `test/shiploop_e2e/LEARNINGS.md`, "Wide-item rule (B) live check").
B needs reliable per-step paths first (F1, the owner's call). **Update 2026-10-27:** F1 is dropped; [design C](shiploop-measured-width-design-2026-10-27.md) measures each step's change instead of reading declared paths, and reviews at the item's end, one review per group; not built. Earlier status: B built, not released (2026-10-27). The owner chose B without the replay ("Skip X1 and build design B
(per-step reviews for wide items) with its fail-first tests and change note"). It is described under "Built" at the end of
§3. The design itself came first, with nothing built ("Design the wide-item review fix here … build nothing yet").

Consumer: first the owner, deciding whether to build and which option, then the session that builds it. This design
follows P0 of [the script-navigated steps design](shiploop-script-navigated-steps-design-2026-10-26.md) (Improve rule
`item`, released in 2.17.0). It acts on the P0 live check's open finding, in `test/shiploop_e2e/LEARNINGS.md`, entry
"P0 + TS1/IN1 live check".

**The question.** P0 replaced the Improve review after each implement step with one review per work item. On Sonnet
battleship that item spanned the whole app, and its one review missed all three defects the per-step baseline fixed.
Two fixes were proposed:
- **A.** The item review's handoff names each step's diff and the component edges.
- **B.** An item that spans several components keeps per-step reviews.

**Evidence.** Four battleship runs, with their records under `~/e2e-runs/`:

| model | before P0 (per-step reviews, 2.16.0) | after P0 (item review, 2.17.0) |
|---|---|---|
| Sonnet 5.5 | `20261026/live-sonnet-battleship-01b9b3` | `20261027/v2170-sonnet-battleship-491d9a` |
| DeepSeek flash | `20261026/ds-flash-978478-battleship` | `20261027/v2170-ds-battleship-759a03` |

Each Improve stage keeps `.shiploop-improve/<stage>-<id>/handoff.md` and `reviews/review-<n>.md`. Each step-plan
result records `steps[].paths`, and `probes.md` holds the probes of the shipped products. The tables derived for this
design are in [`docs/experiments/e2e-v2170-validation-20261027/`](experiments/e2e-v2170-validation-20261027/):
- `review-passes.txt`: every Improve stage of the four runs, pass by pass;
- `item-width.txt`: every work item of the 12 recorded runs with step plans (19 items), made by `item_width.py`.

## 1. What the runs show

### 1.1 Where each catch came from

| defect | per-step baseline (Sonnet 01b9b3) | Sonnet item review (491d9a) | DeepSeek item review (759a03) |
|---|---|---|---|
| `GET //` kills the server (`new URL` outside any try) | S3's review, which read `server.js` whole (2d7c7e7) | missed, shipped: the process exits | W2's review, pass 2 (77095e7) |
| options never validated | S1's review of `game.js`'s `createStore` | missed, shipped: `createServer({maxGames: 0})` evicts every new game, and `-1` loops forever | absent: `createServer` validates its only option |
| a stale fire reply lands on the new game | S2's review of `index.html` (b46f76b) | missed, shipped | absent: New game is locked while a shot is in flight |

- Each defect sat inside one component, at its own entry point or its own state.
- Each was found by the review of the step that built that component.
- None sat at an edge between two components.

### 1.2 What Sonnet's item review did

Its Improve stage, `implement-fbeb9800`, covered W1's three steps:
- S1 `game.js`;
- S2 `server.js`: the routes, the game store and a stub page;
- S3 `server.js`: the real inline page.

The handoff carried the item's whole diff (6aa5193..c297c3f), every step's task and criteria, and the last step's
result by value. S1 and S2 had one "Accepted step" line each.
- **Pass 1** read `game.js`, `server.js` and every criterion, and found three defects:
  - `fire()` and `newGame()` checked no arguments;
  - the 500 path swallowed its cause;
  - the server declared no access posture.

  It fixed them (388263d). It applied Code craft 2 ("fail at the door") to `game.js`, but not to
  `createServer({maxGames})` in `server.js`.
- **Pass 2** re-read both files, confirmed pass 1's fixes and the criteria, and was classified trivial, which ended
  the loop.
- The review took 1.6 awake minutes. The baseline's three step reviews took 2.7.
- **The handoff did not lack information.** The review had both files whole. S2's own result points at none of the
  misses: its `not_covered` is empty, and its decisions cover the 413, the port and the route table.

### 1.3 Sonnet makes one finding pass per review; DeepSeek keeps going

From `review-passes.txt`. A finding pass is a non-trivial pass: it found something and changed it.

| run | Improve stages | most passes in one stage | most finding passes in one stage |
|---|---|---|---|
| Sonnet 01b9b3 | 11 | 2 | 1 |
| Sonnet 491d9a | 8 | 2 | 1 |
| DeepSeek 978478 | 22 | 5 | 4 |
| DeepSeek 759a03 | 10 | 12 | 11 |

- **Superseded 2026-10-27 by the 2.18.0 run, in which 5 of 8 Sonnet stages made two finding passes: depth per review varies by run.**
  The original reading follows.
- **Sonnet never made a second finding pass, in all 19 of its stages.** Each stage's second pass checked the first
  pass's own edits and ended the loop.
- **On Sonnet, then, the number of reviews sets how many finding passes the code gets.**
  - Three step reviews gave each of three components a finding pass.
  - One item review gave the whole app one.
- **P0 assumed "one review can fix several defects, because Improve keeps passing until a pass is trivial".** That
  holds on DeepSeek and fails on Sonnet.
- **DeepSeek's item reviews went deeper than its step reviews.**
  - Its 12 step reviews in 978478 made 4 finding passes and 3 code fixes in 28.0 minutes.
  - Its 3 item reviews in 759a03 made 4 finding passes (W2 twice, W3 twice) and fixed 9 material defects in 10.4
    minutes.

### 1.4 How wide the items were

`item-width.txt` lists each item's steps and their declared paths. A step with no paths takes the item's, as
`shiploop_loops.implement_scope` does. Steps that share a path are joined into one group.

| width | items |
|---|---|
| one group | DeepSeek 759a03 W1 (`battleship.js` in every step) and W2 (`server.js` in every step); DeepSeek 978478 W1 (`lib/game.js`, 4 steps) and W3; chess 12a23d W1 (6 steps, the engine); csv-report W1; the hello runs; every one-step item |
| several groups | Sonnet 491d9a W1 (`game.js` / `server.js`, `server.js`): 2; Sonnet 01b9b3 W1 (`game.js` / `index.html` / `server.js`): 3; DeepSeek 978478 W2 (`server.js` ×4 / `README.md` / `test-support/`): 3; DeepSeek 759a03 W3 (`browser-check/cdp.js` / `public/index.html` ×2): 2; chess 12a23d W3 (the LWC board ×2 / its tab, app and page metadata): 2 |

- Five of the twelve multi-step items are wide.
- Catches were lost only where one Sonnet review covered several groups.
- **A path group is not always one component.** In 491d9a, S2 (routes and store) and S3 (the page) share
  `server.js`, yet they are two components. Two misses were S2's and one was S3's.

## 2. The options against that evidence

### A. The handoff names each step's diff and the component edges — not recommended

- **Each step's diff.** For these new-file steps, S1's diff is `game.js` whole and S2's is `server.js` whole. Pass 1
  had already read both, and had the item diff (1.2).
- **Component edges.** None of the four defects sat at an edge (1.1). DeepSeek W2's one fix near an edge was the page
  checking the server's answer. The review focus already lists that rule (Code craft 6), and a review of the page's
  step reads the same fetch code.
- **It leaves Sonnet's limit as it is:** one finding pass per review (1.3). It would add handoff text with no measured
  effect, which the concise-change rule cuts.

### B. Wide items keep per-step reviews — recommended

- **On Sonnet** it restores what the baseline had: one finding pass per component. The baseline's three step reviews
  made all three catches.
- **On DeepSeek** it changes little.
  - Of 759a03's three items only W3 is wide. Its S2 and S3 changed no file, so it still gets one review (the no-change
    skip in §3).
  - Its narrow items keep the item reviews that fixed 9 defects.
- **The signal is the step plan's `steps[].paths`,** already recorded and read by script. The rule needs no model
  judgement, and it is generic: chess's metadata step forms its own group, just as `server.js` does.

### B′. One review per run of steps that share paths — considered, not recommended

- One review would follow the last step of each run of consecutive steps that share paths.
  - 491d9a W1 gets two reviews (S1; S2–S3).
  - 978478 W2 gets three instead of six.
- It is cheaper on DeepSeek's wide item, but it repeats the failing case.
  - In 491d9a, S2 and S3 share `server.js` and are two components.
  - B′ gives them one Sonnet finding pass between them.
- The eval priority is quality first, then tokens, so B.

## 3. The design (B)

Rule `item` keeps its name (one term per concept) and gains one condition.

- **Narrow item:** its steps' paths form one group, or it has one step. Behaviour is unchanged from P0: one review
  after the last accepted step, over the item's whole change from `item_base`.
- **Wide item:** the paths form two or more groups. Each accepted step gets its own review of its own change (`base`
  to the bound tree). The handoff is the per-step one: that step's Step block, its result by value, and the focus for
  that step. This is the review the item got before P0, kept for these items.
- **No-change skip, per step of a wide item:** a step whose own change is empty (its action's `after` equals its
  `base`) gets no review. P0's P4 asks the same question of the whole item.
- **Groups** come from the accepted step plan: steps that share a path are joined, and a step with no paths takes the
  item's (`implement_scope`'s rule). They are computed from `step_view(...).steps` when needed, so nothing new is
  recorded.
- **The ask-agent route is unchanged.** It builds every step in one action, so its one review follows that action.

Where it lands:
- `shiploop_loops`: a pure `step_path_groups(steps, item_paths) -> int` beside `implement_scope`, with the same
  fallback.
- `shiploop_navigator._improve_checkpoint`, rule `item`:
  - a wide item reviews each accepted step that has a non-empty change;
  - a narrow item reviews only its last.
- `shiploop_navigator._item_steps` returns None for a wide item. `_item_review_lines`, `_review_base_line`,
  `_goal_lines` and `_several_steps` then take the per-step branches they already have.
- The words: the glossary's "Improve stage" row, the comment on rule `item` in `shiploop_stage_spec`, and a change
  note `changes/shiploop/wide-item-step-reviews.md` (`bump: minor`, since it changes the review schedule). The note
  says that it amends the owner's 2026-10-26 P0 rule.

Tests, fail-first and through the real CLI, in `test/shiploop-navigator-contract.test.py` beside
`test_a_three_step_item_starts_one_improve_stage_after_its_last_step_over_the_whole_item`:
1. **491d9a's shape.** A three-step item on `game.js` / `server.js` / `server.js` starts an Improve child after each
   step. Each handoff's review base is that step's own base tree, and its Step block names that step.
2. **One group, unchanged.** The existing three-step, one-group test still starts one child, after S3.
3. **No change, no review.** In a wide item, a step that changed no file starts no child (759a03 W3's shape).
4. **The helper.** 491d9a W1 → 2, 01b9b3 W1 → 3, 759a03 W2 → 1, and a step with no paths takes the item's.

Then run the quick tier with `--changed-from`, and the suites that pin packet counts (`SMALL_HOME_FINGERPRINTS`, and
e2e-efficiency's 32 packets and 8 handoffs). A fixture item that is wide shifts its count; re-pin it with the reason.

**Built (2026-10-27).** It went as planned above, plus three points the build settled:
- The rerun line of the Improve hand-off now reads "the item's test stage, after its last step, runs over it". That is
  true for a wide item's earlier steps too.
- Two P0 tests had fixtures whose steps each wrote a separate file, so under B they became wide items.
  `test_the_items_last_implement_step_starts_its_improve_child_in_both_planning_review_modes` (navigator contract) and
  `test_the_inline_item_handoff_names_the_steps_as_the_ask_agent_one_does` (delegation) now give their steps one group,
  and they still pin the narrow item's single review.
- The other skill touched is the Run Review stage catalog's implement check text, with its own patch note.

Fail-first, all through the real CLI except the helper:
- `test_a_wide_item_starts_an_improve_stage_after_each_step_over_that_steps_own_change`;
- `test_a_wide_items_step_that_changed_no_file_starts_no_improve_stage`;
- `StepPathGroupsTests` in `test/shiploop-loops.test.py`.

Before the change, the two CLI tests failed (S1 got no review) and the helper tests errored (no
`step_path_groups`).

**Review count on the recorded plans** (steps that changed no file still counted, except where noted):

| plan | per step (before P0) | P0 (item) | B |
|---|---|---|---|
| Sonnet 491d9a | 3 | 1 | 3: about +1.1 awake minutes over P0, back to the baseline's 2.7 for these reviews |
| Sonnet 01b9b3 | 3 | 1 | 3 |
| DeepSeek 759a03 | 9 | 3 | 3: W3's S2 and S3 changed no file |
| DeepSeek 978478 | 12 (28.0 min) | 3 | 8: W2's six step reviews took 10.4 min in the baseline, plus two item reviews |
| chess 12a23d | 10 | 3 | 5 |

## 4. Before building: X1, a replay on 491d9a's own code

**Why.** The baseline's code was shaped differently from 491d9a's. It had a store in `game.js` and the page in
`index.html`. So "a per-step review of 491d9a's code finds the misses" is a prediction nobody has tested.

**How.** A replay tests it without a harness run:
- Make two `git archive` copies of 491d9a's worktree history, never the worktree itself:
  - one at db4205d (after S2);
  - one at 56ce960 (after S3).
- Run one Sonnet 5.5 review per step, with the improve skill and its passes as in a run.
- Give each review the per-step handoff for its step: that step's Step block, result and diff, laid out as in the
  baseline's `implement-1f17cb21/handoff.md`. The handoff is rebuilt by hand, which is this replay's fidelity risk.

**What it decides.**
- Build B if the S2 review finds `GET //` or the `maxGames` defect, and the S3 review finds the stale reply: 2 of the 3,
  or all 3.
- Otherwise the per-step catches came from the baseline's code shape, not from the number of reviews, and the design
  goes back to the owner.

**Cost:** two Sonnet reviews, about 3 minutes.

## 5. How to tell it worked, after the build

| run | must hold | should improve | watch |
|---|---|---|---|
| Sonnet battleship (`--backend anthropic`) | PASS; no send-back to implement | when the plan has a wide item, its step reviews fix 2 or more of the 3 defect classes, checked on the shipped product by the probes in `probes.md` | Improve awake minutes, against 01b9b3's 9.4 and 491d9a's 8.7 (forecast about 9.8) |
| DeepSeek battleship | PASS; no send-back to implement | Improve minutes within 10% of 759a03's 62.7 when its items are narrow | how many items are wide, and what their extra reviews cost |

- The report gives each item's group count. A run whose items were all narrow did not exercise the rule, and it says
  so.
- The results are n = 1 per model. A regression is rerun before it decides anything.
- Keep the Mac awake (lid open, keep-awake on) for the Sonnet run.

## 6. Decisions for the owner

- **D1. Which fix.** Recommended: B, with "wide" meaning more than one path group. The alternatives are A (the handoff
  text) and B′ (one review per run of steps that share paths).
- **D2. X1 first.** Recommended: run the replay (§4) before building. The alternative is to build B and measure it live.
- **D3. Outside this change.** Sonnet's one finding pass per review affects every Improve stage, not only implement.
  Whether a second pass must read the code the first pass left unchanged is a question for the Improve skill, with its
  own measurement.

## Not in this design

- Changing Improve's pass loop or its stop rule (D3).
- The ask-agent route.
- Recording component boundaries beyond the paths the step plan already declares.
