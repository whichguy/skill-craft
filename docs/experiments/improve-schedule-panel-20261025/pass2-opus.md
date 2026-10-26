### 1. Hold

- Nothing to hold. My pass-1 seat failed (exit 6, "config/limit failure (max-turns/options)") and returned no text. Every item below is new. I checked each one against this worktree (HEAD `49aebb77`) and the run folders under `/Users/dadleet/e2e-runs/`, and edited nothing.

### 2. Augment / revise

#### `REVISE (own):`
- **From:** no answer.
- **To:** my verdicts:
  - **P1:** keep, but measure a different file (Codex's rule).
  - **P2:** keep, reworded so a replay checks that each input is allowed, and so it covers examples the review itself adds.
  - **P3:** drop the skip and narrow the re-review instead.
  - **P4:** not a skip rule yet. Run it in shadow mode, and reuse the review of a reissued step that has not changed.
  - **P5:** keep the end-of-work item, and pilot a required reason for each survivor at test-stage done.
  - **P6:** keep.
- **Why:** the items below.

#### `ADOPT Codex:`
- **Claim:** P2's account of the cause is wrong. The run 5b test-strategy review added TC_28 itself, then "replayed" it with a helper that has no legality check.
- **Why:**
  - **The review added the case.** `test-strategy-edacefd5/reviews/review-1.md` says: "Changed: Added `TC_25_pin` and `TC_28_promoFromStart`". Its learnings section records the illegal line `b2b4 b7b5 b4b5 …` as correct.
  - **The replay could not catch it.** `checks.md` says: "replayed with `run/scratch/oracle_replay.py` `apply_simple` (no legality generator). Exit 0."
  - **So the proposal's own key case contradicts it.** It says "the reviews that did replay found errors, so the yield is in replaying". Here a replay happened and approved the illegal line.
  - **P2's draft text would have passed that review.** "Replay the sequence … and record the replay" is satisfied by what it did.
  - **Kimi's script suggestion has the same hole.** Sending mechanical cases to a script in `.experiments` repeats this failure unless the script checks that each input is allowed.
- **Replacement item text** (generic, about +420 characters against the 20,000 cut):
  > "an expected result derived from a sequence of inputs (actions, calls, records), including one this review adds or changes: from its stated start state, check that each input is permitted under the spec's own rules, naming the rule that permits it, then recompute the result. A helper that applies inputs without checking they are permitted is not a replay, and neither is the product under test. Record the case, the method and the computed result in the review; mark a result you did not check `NOT-REPLAYED: <reason>`."
- This combines Codex's check of every transition, Kimi's rule citation and Kimi's `NOT-REPLAYED` exit. The escaped send-back is **n=1**.

#### `ADOPT Codex:`
- **Claim:** count the defects a review introduces, not only the ones it finds. The owner's question was whether Improve adds real value, so the net matters.
- **Why:**
  - TC_28 was introduced by Improve. It cost the W1 send-back: in run 5b's state history, row 14 is the implement W1 send-back, and rows 15–16 redo step-plan and test-spec. It also cost an org deploy.
  - The proposal's table books test-strategy as 3 DEFECT finds and records no debit.
  - **Measurement to add:** per review, "defects introduced" next to "defects found". A pass that repairs the same review's earlier edit is not a find.

#### `ADOPT Codex:`
- **Claim:** P1 hashes the wrong file. Also, the metrics do not inherit the pass log.
- **Why:**
  - In run 5b, `test-spec-4fb41465/reviews/review-1.md` hand-off says: "pass 1 edited the pending result at `run/inbox/nav-6d9c61d3….md`". It adds that "the parent return uses `--final-result` once the child receipt is complete".
  - So hashing only `<action>-final-result.md` attributes the edit to the return, not to pass 1.
  - `metrics.improve_reviews` (`test/shiploop_e2e/metrics.py`) never reads `passes.md`. It sets `seconds = max − min` over the review files' modification times, so a one-pass review reports 0 s. P1's "every reader of the pass log inherits it" is wrong for the metrics; that fix is new code there.
- **Rule to take:** Codex's replacement. Record the content identity of the candidate under review, with the frozen producer result as the baseline, and treat missing evidence as "unknown", not "unchanged".

#### `REJECT Kimi:`
- **Claim:** "`unchanged_first_pass` is tree-only … the single most important correction", so P1 changes behaviour.
- **Why:** under ShipLoop's current setting the flag is never set.
  - `IMPROVE_TRIVIAL_REVIEWS = 1` (`shiploop_navigator.py`) is passed as `required_trivial_reviews`.
  - `until_loop_ephemeral.py` completes as soon as `trivial_streak >= required`, which is already true after any trivial first pass.
  - It writes `progress.unchanged_first_pass` only when `trivial_streak < _required_trivial_reviews(current)`, which is false when the requirement is 1.
  - So `count = 1 if _unchanged_first_pass(child) else IMPROVE_TRIVIAL_REVIEWS` gives 1 either way. The restart refusal in `_improve_change_gate` ("ended on one unchanged trivial pass, but these files changed …") cannot fire.
- **Consequence:**
  - Redefining the flag changes nothing.
  - The real stop rule is the model's own "trivial" classification. There is no Git cross-check, and tree edits and result edits are treated alike.
  - That is by owner decision (`references/improve-stages.md`: "completes at the first pass that finds only trivial changes or none", 2026-10-20). Making every edited pass non-terminal would bring back the confirming pass that decision removed.
  - So P1 stays telemetry-only. The proposal's "one unedited pass ends a review" should say "one trivial pass" (Codex said so too).
  - The flag and the restart gate are dead code under ShipLoop's setting. Removing them is cleanup, not a measured gain.

#### `ADOPT Codex:`
- **Claim:** P3's rule, as written, does not remove the re-reviews it counts.
- **Why:**
  - In run 5b's history, row 14 is the implement W1 send-back and row 16 is test-spec W1 `856264e1`.
  - `_first_item_review` returns True when `item == first`, whether or not there was a send-back.
  - So deleting the send-back clause still re-reviews `856264e1`, which is 3.4 of P3's 5.7 minutes.
  - Any skip needs a different check: "this is the item's first test-spec result", i.e. no earlier accepted test-spec row for that item.

#### `REVISE (own):`
- **From:** (new) P3 verdict.
- **To:** drop the skip and narrow the re-review. Rule text:
  > "After a send-back, the test-spec review reads the case rows that changed, were added or were dropped since the item's previous accepted test spec, and the rows that depend on them; it does not re-review unchanged rows."
- **Why:**
  - `856264e1/reviews/review-1.md` reads all 25 cases (3.4 min), yet "Only TC_28 changed". TC_28 is the changed derived value that Kimi and Codex both say must keep a review.
  - Under Kimi's carry-over rule this review would still run, so the conditional skip saves at most about 2.3 min over three runs (about 0.8 min per run).
  - Narrowing keeps focus item 5's check for dropped IDs and still cuts the cost. Kimi says the changed-row list is script-checkable through `_sent_back_results`' `spec_before`; I did not verify that.

#### `ADOPT Codex:`
- **Claim:** P4's evidence about later steps comes from one run.
- **Why:**
  - Run 3's implement packets say "Step S1 (1 of 1)" (for example `nav-aa400925…`). Run 5b's say "Step S2 (2 of 6)".
  - So "the other 12 steps found 0" splits into 10 from run 5b and 2 from run 3. The run 3 pair were first steps excluded by the path-type condition.
  - The "first step" half of the trigger therefore rests on **n=1 run**, with one way of splitting steps. Add Kimi's and Codex's point that on a metadata-driven platform the metadata is the behaviour.
  - With quality first, that does not justify skipping.
- **Verdict:**
  - Run P4 in shadow mode. Each step's `passes.md` records "would skip under IMP-4" and why, and the review still runs.
  - Decide at IMP-4's re-decision point, and only with at least one more multi-step run, preferably in another domain.
  - The one cut I would take now is Codex's: reuse the review of a reissued step whose candidate, contract and proof evidence are unchanged.
  - Codex's point on lint scope is confirmed. The `_step_entry` docstring says an item's earlier steps stay uncommitted until verify, and lint keeps a per-item base (`_item_base_path`). So "the step's lint scope" accumulates across the item. That over-reviews rather than under-reviews, but the step's own base from `_step_entry` is the exact input.

#### `REJECT Kimi:`
- **Claim:** P4 as "change the exclusion list, keep everything else", i.e. skip every later step, said to rest on "n=5 defects, n=3 runs".
- **Why:** runs 3 and 4 contributed no later-step observations (packets above). The skip of later steps is fitted to one run.

#### `ADOPT Codex:` / `REJECT Kimi:` (P5, question 4)
- **Claim:** the test stage should require a reason (a "disposition") for each in-scope survivor, not a kill, before done. Pilot it, and keep the end-of-work item as a final check against the finished candidate.
- **Why:**
  - **Partial survival passes silently today.** The `mutation_check` docstring says it is "Refused only when at least one mutant ran and none was killed".
  - **The end-of-work review is not guaranteed.** `_improve_due` runs it only when `work_index + 1 >= len(work_items)`, and run 3 never got there. So the proposal's own run 3 survivor (`src >= 0`) would still go unaddressed under P5 as written.
  - **Kimi's three objections do not hold:**
    - "Equivalence is a judgment": the gate checks only that a reason is present, and the judgment is recorded.
    - "Reruns a whole item": the refusal happens inside the test stage's own fix loop (`complete --check-only`), not as a send-back.
    - "Uneven for remote-only items": the rule binds only on recorded survivors. A skipped check has none, and `shiploop_mutation.py` already records the skip.
  - Its cost is unmeasured, and only two runs had survivors, hence a pilot.
  - Keep test-spec's weak-assertion focus (Kimi and Codex agree).

### 3. Still open

- **Whether the product counts as evidence.** `856264e1` accepted the fixed line because it was "already observed in the org", i.e. the product engine accepted it. An engine that accepts a line does not prove the line is legal. Which reference counts as independent stays open.
- **P6's count (Codex says 10 edited spec passes).** The classifications show 9 non-trivial spec passes (5 + 2 + 2). A tenth edit would be a trivial-pass polish. This does not change the verdict.
- **P4's realised saving.** Run 3 predates the one-pass rule, so under current rules the saving would be below the proposal's 15.9 minutes (Kimi's point).