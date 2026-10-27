# Script-navigated steps, starting with the test stage, and a trimmed Improve schedule — design, 2026-10-26

Status: **P0 built, not released** (2026-10-26, owner's go: the change that adds
`changes/shiploop/improve-once-per-item.md`); P1–P3 are design only. P0's validation runs need a release first.

Update 2026-10-27: P0 shipped in 2.17.0 and was checked live. Its item review missed Sonnet's defects when one item
spanned the app; the follow-up is [the wide-item review design](shiploop-wide-item-review-design-2026-10-27.md).

Consumer: the owner, deciding what to build, then the session that builds it. The owner asked for "discrete steps in
the prompts that are actually navigated by the shiploop scripts", which can be visualized, starting with the test stage.
It also folds in the trimmed Improve schedule: drop the test-spec review, and run one implement review per work item.

The evidence comes from four runs at skill-craft 2.16.0 / ShipLoop 1.15.0, all under `~/e2e-runs/20261026/`:
- DeepSeek flash hello (`pilot-ollama-dsflash-993a9d-hello`) and battleship (`ds-flash-978478-battleship`);
- Sonnet 5.5 hello (`live-sonnet-hello-b01d1c`) and battleship (`live-sonnet-battleship-01b9b3`).

Each run's `RUN/trace.jsonl` (packets and command callbacks), `RUN/tests/*.md` (ShipLoop's test records) and
`.shiploop-improve/*/reviews/` (Improve passes) are the records. The runs are journaled in
`test/shiploop_e2e/LEARNINGS.md`.

## The rules this design keeps

- **Scripts navigate; the model does one step and reports it.** The model never holds position (ShipLoop's purpose,
  2026-09-24; the stateless-skill rule, 2026-10-11).
- **Context can be cleared between any two steps.** Each packet restates its stage, item and step, by value
  (2026-10-07).
- **One step at a time.** Each stage's script returns a template prompt with named slots (2026-10-18).
- **A script-run test is the evidence,** never a model's claim (2026-09-26).
- **Generic.** No stack rule enters ShipLoop.
- **KISS.** Change one thing at a time, and measure it on a live run.

## 1. What the test stage is today

`test` (`shiploop_stage_spec`, the `Stage("test", "inner", ...)` row) is one action:
- its goal is "Write a test per quoted case, titled with its ID; make every recorded command pass in WORKTREE";
- it edits code and tests;
- `entry_runs=("loop-contract",)`;
- `complete_runs=("loop-terminal", "lint-gate", "test-base", "test-loop")`.

The model gets one packet with eight numbered duties: write the cases, test decisions, gaps, run and fix, end states,
result fields, proof limits, send-back. It also gets four exit conditions and a result template. It works through them
inside its Until Loop, then calls `complete`. ShipLoop then runs three checks itself (`shiploop_test_loop`):
- `base_check`, the RED check on the item's base;
- `loop_run`, every recorded command on the candidate;
- `mutation_check` (`shiploop_mutation`).

`complete --check-only` previews the same checks, and an unchanged tree reuses their records: the accepting
`complete` of battleship's W2 took 1.4 s.

What the records show:

| run | test actions | minutes | packet chars | callbacks (check-only / accept) | refusals |
|---|---|---|---|---|---|
| DeepSeek hello | 1 | 2.8 | 41,682 | 2 / 1 | 1 field shape (`red_na`) |
| DeepSeek battleship W1 | 1 | 3.3 | 37,861 | 2 / 1 | 1 mutation (1 of 8 survived) |
| DeepSeek battleship W2 | 1 | 8.5 | 66,984 | 6 / 1 | 3 fields (`not_covered`, `decisions`, `red_na`), 2 mutation (2/8, then 1/8) |
| DeepSeek battleship W3 | 1 | 5.1 | 42,684 | 2 / 1 | 1 mutation (5 of 8) |
| Sonnet hello | 1 | 0.5 | 25,103 | 1 / 1 | none |
| Sonnet battleship | 1 | 7.8 | 39,653 | 3 / 1 | 2 mutation (4/8, then 1/8) |

- **The checks are cheap and the model's time is not.** A focused run takes about 2.2 s and a base run 0.15 s. A
  mutation check with survivors takes about 70 s, and an unchanged tree reuses its records. Nearly all of W2's
  8.5 minutes was the model writing and fixing tests.
- **The mutation check is the stage's real loop on both models:** 4 refusals on DeepSeek, 2 on Sonnet. Today the
  model learns of survivors only after it believes it is finished. It then works the fix from a 38–67k packet, with a
  one-line refusal string as the new input.
- **The other refusals are result fields the model filled wrongly:** fields that belong to implement, and the
  `red_na` shape. ShipLoop holds the data for most of those fields in its own records.
- **The packet carries everything at once.** W2's 66,984 characters break down as:
  - the test-spec cases, 25.6k;
  - the step plan's `follows`, 9.9k;
  - stage guidance, 8.4k;
  - the result template, 7.4k;
  - implement's `not_covered`, 6.8k;
  - the exit conditions, 2.9k.

  Writing the cases needs the first and the fifth. The result template matters only at the end.
- **ShipLoop sees only `complete`.** The flow viewer (`test/shiploop_e2e/flow.py`, each action's `phases`) shows one
  producer row for the whole stage, so where its time went is not visible.

## 2. The design: T1–T5, navigated by ShipLoop

The test action becomes five steps. ShipLoop holds the cursor (the action and its step) in the run state and prints
one template packet per model step. The model calls one callback per step and never chooses the next step.

| step | who | the packet's slots (by value) | what ShipLoop then runs or checks | on failure |
|---|---|---|---|---|
| T1 write the tests | model | stage, item and step header; the test-spec cases; implement's `not_covered`; the harness and suite decision; the write rules (ID as its own word in the title, cases before code) | that every test-spec ID is in a test file, a cheap read check before any run | fix packet F1: the missing IDs |
| T2 RED on the base | ShipLoop | — | `base_check`: a new ID must not pass on the item base | fix packet F2: the IDs that pass on the base, each to be tightened or named in `red_na` with a reason |
| T3 GREEN, regression, lint | ShipLoop | — | the lint gate, then `loop_run`: every recorded command exits 0, lists its IDs and meets its floor | fix packet F3: the failing command's output and the cases it covers; fix code or test (with a reason), or send back |
| T4 mutation | ShipLoop | — | `mutation_check` on the item's changed product lines | fix packet F4: each surviving mutant (file, line, change) to be strengthened or disposed of |
| T5 report | model | the prefilled result: case end states from T3, `red_na` from F2, the edited tests from the diff since T1 | the result's form, as today | the existing field refusal, now only on the few fields the model writes |

Navigation rules, all script-owned:
- **A change sends the run back to RED.** Any edit to test or code files after T2 re-enters at T2, derived from the
  tree fingerprint. ShipLoop reruns only what the tree change invalidates, reusing records as `complete --check-only`
  does today.
- **Send-back stays where the model works.** It is an outcome of T1 and of every fix packet, as duty 8 is now.
  `blocked` stays as today.
- **No cap on fix loops.** No count stops the work, the same as `refused_runs` today (owner, 2026-10-24: no run caps).
- **The exit conditions map onto steps.**
  - "Every case … is a test the focused command runs, with its ID in the name" becomes T1's read check plus T3's ID
    listing.
  - "No new test ID passes on the item's base" becomes T2.
  - "One complete iteration after the last edit …" becomes T3, which reruns after the last edit by the re-entry rule.
  - "Every test change made to pass a run has a recorded independent reason" becomes T5. ShipLoop lists the test edits
    made after a T3 failure, and the model gives one reason each.
  - The mutation check is T4, as `complete_runs` orders it now.

Packets:
- **Template text, slots by value.** Each packet restates the stage, the item and the step in its header, so a cleared
  context can do the step from the packet alone.
- **Smaller packets.** For W2, T1 needs about 25.6k plus 6.8k of slot data and a few thousand characters of
  guidance, roughly half of today's 67k. A fix packet carries only its failure and the cases it touches, a few
  thousand characters. T5 carries the prefilled result, not the 7.4k template.
- **No duties that don't apply.** "Proof limits" (duty 7) stops being prose the model must apply: T3's count and ID
  rules already enforce it.

Visibility:
- **`flow.json` gains a step phase.** Each test action's `phases` gains `{"kind": "step", "key": "T1" …}` entries,
  with start, end, outcome and the record each step wrote. `flow.html` draws them as rows under the action, so the
  owner sees, for example, "T4 mutation: 2 of 8 survived, F4, T2 again, T3, T4 passed".
- **The trace records each step.** `RUN/trace.jsonl` gets one event per step.
- **The status card names the step.** The e2e builder (`status_card.py build e2e`) shows the running step:
  `test · T3`.

What stays the same:
- the check code (`base_check`, `loop_run`, `mutation_check`) and the count rules (`shiploop_test_counts`);
- the lint gate;
- the test records under `RUN/tests/`;
- the stage's place in the inner loop;
- its allowed outcomes.

## 3. The trimmed Improve schedule

Before P0 (`shiploop_stage_spec.IMPROVE_RULES`, each `Stage(..., improve=...)`, read by
`shiploop_navigator._improve_checkpoint`):

| rule | stages |
|---|---|
| `always` | spec, test-strategy, plan, system-test-author, release-plan |
| `first-item` | step-plan, test-spec |
| `step` | implement (every accepted step, owner 2026-10-10; P4 skips a reissued step that changed no file) |
| `last-item` | carry-forward |

Proposed (owner direction, 2026-10-26; built in P0):

| stage | today | proposed | evidence (reviews that found something) | DeepSeek battleship minutes |
|---|---|---|---|---|
| test-spec | `first-item` | none | 2 real catches in 14 reviews over seven runs (a third only confirmed scope) | 9.9 (2 reviews, W1 twice after its send-back) |
| implement | `step` | `item`: one review of the item's whole diff after its last implement step, before its test stage | 11 of 40 reviews over seven runs; DeepSeek 3 real code fixes in 12, Sonnet 3 in 3 | 28.0 (12 reviews) |
| the rest | as today | as today | spec, test-strategy, plan and carry-forward almost always; system-test-author and release-plan pay on DeepSeek | — |

- **Why after the last implement step:** the fixes land before the test stage writes the tests, so the tests cover
  the fixed code.
- **P4 still applies:** an item that changed no file since its last review gets none.
- **Estimated effect.**
  - DeepSeek battleship: 22 reviews become 11, and about 31 of its 86 Improve minutes are saved (14% of the run). That
    assumes an item review costs about what a step review did (2.3 minutes); a larger diff may cost more.
  - Sonnet battleship: 11 reviews become 8, about 2 minutes.
- **The risk is Sonnet's three real per-step bugs:**
  - `GET //` crashed the server;
  - a shot still in flight landed on the new game;
  - the store's options were never validated.

  One item review must find them all. It can, because Improve keeps passing until a pass is trivial, so one review can
  fix several defects. Whether it does is what validation measures.
- **It supersedes the owner's 2026-10-10 rule** "every accepted implement step is reviewed", so the change note says
  so.
- **Step-plan keeps its `first-item` review.** Its costliest miss is better made a script check: W1's unmeetable
  Proof cost about 24 minutes of rework. That is improvement 1 of
  `docs/shiploop-deepseek-run-improvements-plan-2026-10-26.md`.

## 4. Build order

Each phase is its own change, with a fail-first test through the real CLI and a change note. A release is the owner's
call. Each phase is followed by one DeepSeek battleship run (the E2E default) and one Sonnet run
(`--backend anthropic`), both journaled.

1. **P0: the Improve schedule.**
   - Add the rule `item` to `IMPROVE_RULES`, give implement `improve="item"`, and give test-spec no rule.
   - `_improve_checkpoint` starts an implement review only after an item's last implement step.
   - Tests: a three-step item yields three implement actions and one Improve child, after the third; a test-spec
     result starts no child. This is a small change and measures on its own.
   - **Built (2026-10-26).** What the build settled beyond the plan above:
     - The item review covers the item's whole change. Its diff base is the tree before the item's first step
       (`item_base`, carried from step to step in the inner-loop action by `shiploop_navigator._step_entry`). Its
       handoff lists every step's task and criteria (`_item_review_lines`), and its focus and goal are worded for
       "steps S1 to Sn" (`_item_steps`).
     - P4 now asks of the whole item: no review when no round of any step changed a file (`round_changed`).
     - On the ask-agent route an item is one action, so its review follows that action, as before.
     - Two mechanisms became dead and were removed (one supported version): the narrowed re-review of a revised
       test spec (the handoff's "Scope of this revision" section) and the IMP-4 shadow line.
     - Fail-first tests, through the real CLI, in `test/shiploop-navigator-contract.test.py`:
       `test_a_test_spec_result_starts_no_improve_stage` and
       `test_a_three_step_item_starts_one_improve_stage_after_its_last_step_over_the_whole_item`. Both failed on the
       code before the change.
2. **P1: T1–T5 for the test stage.**
   - The navigator's cursor gains a step.
   - The packets become templates per step.
   - ShipLoop runs T2–T4 in order, prints fix packets, and prefills T5.
   - Tests:
     - a fake model that skips an ID gets F1;
     - an edited test after T2 re-enters at T2;
     - surviving mutants yield F4 with their lines;
     - T5 arrives prefilled;
     - a cleared context given only the current packet completes its step.
3. **P2: visibility.** Add the `step` phase in `flow.json` and `flow.html`, the trace events and the status-card step,
   with a render test on a fixture run.
4. **P3, later, on the same pattern:**
   - implement: one step's build, then its Proof and lint by script, then a fix packet, then a prefilled handoff;
   - the outer system-test stage.

## 5. How to tell it worked

The baselines are today's battleship rows: DeepSeek in `test/shiploop_e2e/baselines.jsonl`, and Sonnet's 2.16.0 row.

| phase | must hold | should improve | watch |
|---|---|---|---|
| P0 | verdict PASS; no send-back from an outer stage to implement | Improve minutes down 25% or more | each item review's real product fixes, from its `Found:` lines, against the per-step baseline |
| P1 | verdict PASS; the same RED, GREEN and mutation records | no field-shape refusals at the test stage; test-stage packets about half the size | test-stage minutes, and fix loops per item |
| P2 | the render test passes | the owner can read where test-stage time went from `flow.html` alone | — |

These are n = 1 per model. A regression reruns before it decides anything.

## 6. Decisions for the owner

- **D1. Where T2–T4 run.**
  - Today ShipLoop runs the recorded commands itself with `/bin/sh -c` (owner, 2026-09-25), so host hooks don't see
    them.
  - The 2026-10-11 rule says model-triggered commands go through the host shell, with results piped back in.
  - Recommendation: keep in-process runs for P1, so that only navigation changes. Revisit printed, hook-visible
    commands as a separate change.
- **D2. Where the item's implement review sits.** Recommendation: after the item's last implement step. The other
  option is after its test stage.
- **D3. The re-entry rule.** Recommendation: any edit after T2 re-enters at T2, derived from the tree fingerprint.
  The alternative re-enters at the failed step.
- **D4. Surviving mutants.**
  - Recommendation: F4 asks for a test that kills each survivor, or a disposition naming why it is equivalent. This is
    the 2026-10-25 panel's P5.
- **D5. The test stage's Until Loop.** With ShipLoop navigating the fix loop, the stage's `loop-contract` duplicates
  it. Recommendation: retire it for the test stage in P1.

## Not in this design

- Running Improve in parallel. Of all the reviews, only test-spec's could run beside implement, and this design drops
  it.
- Changing what any check accepts. The checks and their rules stay as they are; only who navigates between them
  changes.
