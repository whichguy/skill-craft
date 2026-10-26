# ShipLoop Improve: what it found, and a proposed sharper schedule (2026-10-25)

Status: **reviewed by the advisors panel; awaiting the owner's go.** Nothing here is built yet. The panel revised
P1-P5. Read "Panel outcome" at the end before the proposals: it supersedes them where they differ.

## Why

Improve is the largest overhead in a ShipLoop run. Chess run 5b spent about 84 of its 284 active minutes in Improve
reviews (29%). The owner asked: "Should we determine where `improve` was either inefficient in and of itself or if it
really didn't make any true value? If so, should we be more selective about when and where to run `improve`?" This
document answers that from the records of chess runs 3, 4 and 5b (Grok 4.7 at medium effort, skill-craft 2.7.0, 2.8.0
and 2.9.0), and proposes six changes.

## How the evidence was gathered

- 56 Improve reviews and 118 passes, with every per-pass review file still on disk:
  `<run>/.shiploop-runs/<id>/worktree/.shiploop-improve/<stage>-<id>/reviews/review-N.md`.
- A review counts as **edited** when the git tree changed during it or it left `run/inbox/<action>-final-result.md`.
- Each edited pass was classed by reading its review file and the product files it names:
  - **DEFECT:** it fixed something that would have caused wrong behaviour, a false pass, a broken check, or a plan
    error a later stage would hit;
  - **STRENGTHEN:** it made a test or oracle stronger, with no known failing behaviour;
  - **POLISH:** wording only.
- Manifest: `/private/tmp/…/scratchpad/improve-manifest.json`. The two read-only analyses are summarised below.
  The per-stage numbers are reproducible from the manifest; the classes are a reader's judgment, quoted against the
  review text.

### Correction that changed the conclusion

Each review's pass log (`RUN/improve/<action>/passes.md`) has a column, "tree changed", that compares git trees. The
step-plan, test-spec and system-test-author stages write their reviewed result to `run/inbox/`, outside the tree, so
their edits show "n".
- On that column, test-spec reviews changed nothing in 9 of 9.
- Counting result files, they edited in 5 of 9.
- A decision to drop the test-spec review was nearly made on the wrong number.

## What Improve did, per stage (runs 3, 4 and 5b)

| Stage reviewed | Reviews | Minutes | DEFECT / STRENGTHEN / POLISH passes | Reviews with a DEFECT | Share of minutes in reviews that edited nothing |
|---|---|---|---|---|---|
| spec | 3 | 36.8 | 1 / 7 / 1 | 1 | 0% |
| test-strategy | 3 | 25.2 | 3 / 3 / 1 | 2 | 0% |
| plan | 3 | 18.9 | 6 / 0 / 0 | 3 | 0% |
| step-plan | 10 | 55.8 | 5 / 5 / 0 | 4 | 12% |
| test-spec | 9 | 19.8 | 1 / 5 / 0 | 1 | 29% |
| implement (per step) | 22 | 42.0 | 5 / 0 / 0 | 5 | 52% |
| carry-forward (end of work) | 2 | 16.9 | 3 / 0 / 0 | 2 | 0% |
| system-test-author | 3 | 18.6 | 1 / 0 / 0 | 1 | 32% |
| release-plan | 1 | 2.7 | 0 / 0 / 1 | 0 | 0% |
| **all** | **56** | **236.7** | **25 / 20 / 3** | **19** | **17%** |

**Answer to the owner's question.**
- **Improve is not inefficient in itself.** A review that edits nothing costs one pass, a median of 46 s. One
  unedited pass already ends a review (owner, 2026-10-20); run 3 predates that rule and carried the old two-pass
  confirming cost.
- **Where it loses value is scheduling.** The time goes to reviews that cannot find anything: half the per-step
  implement reviews (52% of their minutes), and every re-review of a test spec after a send-back.
- **It also has one blind spot:** expected values derived from a sequence of inputs that nobody replayed.

Examples of the DEFECTs it found, with the review that found each:
- **plan, run 5b:** TC_19 "names SLChessController before that class exists".
- **step-plan, run 5b:** step S3's proof needed castling "before S4 adds castling".
- **implement, run 5b:** "applyMove accepted e2e4q as e2e4". No test named that string, so nothing else would have
  caught it before the end-of-work review.
- **implement, run 3:** an uppercase square "indexed the board with -1". Run 3 never reached its end-of-work review,
  so no other stage would have caught it.
- **carry-forward, run 5b:** late replies were still applied after New game, and "exactMove returned no move" for an
  underpromotion.
- **test-spec, run 4:** the GREEN wording meant "TC_1 would accept TC_10", so it now requires the exact name. Classed
  STRENGTHEN.

## Proposed changes

### P1. The pass log and the metrics count result edits, not only tree edits

- **Before:** `_passes_text` writes "tree changed" from the runtime's tree comparison, and `metrics.improve_reviews`
  and every reader of the pass log inherit it.
- **After:**
  - each pass records whether the stage's result file (`run/inbox/<action>-final-result.md`) changed in that pass,
    alongside the tree comparison;
  - the pass log shows a column "edited" (tree or result) next to "tree changed";
  - the E2E metrics count a review as edited when either changed.
- **Evidence:** test-spec read as 0 of 9 edited, and was 5 of 9. Step-plan read as 3 of 10, and was 7 of 10.
- **Expected effect:** later schedule decisions rest on the right count. This is a measurement fix with no behaviour
  change.
- **Cost:** one file hash per pass.

### P2. The planning review replays every expected value derived from a sequence of inputs

- **Before**, focus item 1 of `shiploop_prompts._REVIEW_FOCUS_ITEMS`, shared by the spec, test-strategy, plan,
  step-plan and test-spec reviews and printed in the spec and test-strategy duties: "a step, example or expected
  result that cannot be replayed exactly: name the concrete inputs, values, identifiers and sample interactions".
- **After:** the same item, plus: "for an expected result derived from a sequence of inputs (moves, calls, records),
  replay the sequence from its start state under the spec's own rules, recompute the result, and record the replay in
  the review".
- **Evidence:**
  - **Run 5b, W1:** the test-spec review recomputed TC_8's and TC_4's FENs but never replayed TC_28's line, b2b4
    b7b5 b4b5. It is illegal: after b7b5 the pawn on b4 is blocked. Implement found it only after a deploy
    (0Afaj00000p2jgPCAQ) and sent the item back (result `nav-d504330d…`). The step plan was rewritten, test-spec ran
    again, and the item lost about 6–10 minutes.
  - **Spec review, run 3:** "R-9 said the e7 promotion FEN has exactly four legal moves". **Test-strategy review, run
    5b:** "the promotion step could not be replayed". The reviews that did replay found errors, so the yield is in
    replaying.
- **Why it would change behaviour:** the current wording asks that examples be replayable, by naming concrete inputs.
  It never asks the reviewer to replay them. The miss is exactly that gap.
- **Expected effect:** hand-derived expected values are checked at planning time, not after a deploy. That saves a
  send-back cycle whenever such an error exists. In these three runs that was 1 send-back, plus 2 errors the reviews
  caught.
- **Cost:**
  - longer review passes where a plan has long sequences;
  - about +200 characters in the spec and test-strategy duty heads, which print these items (spec head 14,354; the
    cut is 20,000).
- **Risk:** a reviewer "replays" by restating, not computing. The "record the replay" clause makes that visible in
  the review file.

### P3. No test-spec re-review after a send-back

- **Before:** test-spec is reviewed on the first item, and again when a send-back revises the item's plan.
- **After:** the first item only. A revised test spec goes straight on, and step-plan's re-review stays.
- **Evidence:**
  - The 4 test-spec re-reviews edited nothing (run 3 `299cc3e8` 0.6 min, run 4 `13a9da2e` 1.2, run 5b `856264e1`
    3.4 and `29e3f507` 0.5).
  - The 5 first-item test-spec reviews all edited.
  - Step-plan re-reviews found DEFECTs in 2 of 4: run 3, "mv of an existing directory nested it"; run 5b, "A later
    test-spec would have copied them". That is why step-plan's re-review stays.
- **Expected effect:** about 2 minutes per run, with no edit lost in these runs.
- **Risk:** a send-back that changes the cases' premise could go unreviewed. The step-plan re-review sees the new
  plan first.

### P4. IMP-4: review an implement step only where step reviews find defects

- **Before:** every implement step gets a review.
- **After:** a step gets a review only when both hold. Both are script-checkable from the item's current step plan
  and the step's lint scope:
  - it is the first step of its item's current step plan, a re-issued plan included;
  - it changes source code, meaning its scope holds a file other than metadata, configuration, documentation or
    dotfiles.

  The end-of-work review stays for every run.
- **Evidence:**
  - 22 implement-step reviews; 5 found a DEFECT, all of them on a first step that changes source code (5 of 10
    such steps). The other 12 steps, later steps or metadata and config only, found 0.
  - Of the 5 DEFECTs:
    - run 3's (uppercase square) had no other catcher;
    - two (e2e4q; a stale move list after a click) had no test, and the end-of-work review plausibly would have caught
      them;
    - one (a resolved move still applied after New game) the end-of-work review plausibly catches, but not its second
      half (all squares one colour; the page was never opened);
    - one (a script asserting the retired line) the step's own proof would have caught.
  - The other way round, twice the end-of-work review found defects that step reviews had missed.
- **Expected effect:** 12 of 22 reviews skipped, 15.9 minutes over the three runs, about 5 per run on average (13.4
  in run 5b). No DEFECT in these runs would be lost.
- **Risk:** the rule is fitted after the fact on 5 defects; it is n=3 runs. Re-decide it at the next 10 step reviews,
  as IMP-4's own note already says.
- **Rejected:** dropping per-step reviews altogether saves about 14 minutes per run, but misses run 3's defect
  outright and leans on the end-of-work review for three others.

### P5. The end-of-work review reads the surviving mutants

- **Before:** ShipLoop's mutation check records surviving mutants per item (`RUN/tests/*-mutation*.md`), and no
  review is asked to look at them. The end-of-work review focus does not mention them.
- **After:** the end-of-work review focus adds one item: "each surviving mutant recorded in RUN/tests/: add the test
  that kills it, or record why it cannot be killed".
- **Evidence:**
  - Run 5b, W3: 2 of 8 mutants survived in the board component (`nav-9d5cc85f…-mutation1.md`).
  - Run 3: a mutant survived at the engine's `src >= 0` check (`nav-da24c1ff…-mutation1.md`) and was never addressed,
    since the run stopped before its end review.
  - A test-spec review cannot see these, because the code does not exist yet. So removing weak-assertion hunting from
    test-spec and pointing the end-of-work review at real survivors puts the check where its evidence is.
- **Expected effect:** weak assertions are strengthened from evidence, not guesswork.
- **Cost:** a few minutes at the end of work, when there are survivors.
- **Known gap:** mutation is skipped for items whose tests run only on a remote target, so they have no survivors to
  read.

### P6. Spec review stays, watched for cost

- **Before and after:** no change.
- **Evidence:** it is the most expensive per DEFECT (36.8 minutes for 1 DEFECT, 7 STRENGTHEN). But its STRENGTHEN
  edits are the stand-in oracles that F1-F6 were built to stop, and they feed every later stage.
- **Open question for the advisors:** is a STRENGTHEN worth 36.8 / 8 ≈ 4.6 minutes when it sits at the top of the
  chain?

## What we would measure next

On the next chess run and the four step slices, record per stage:
- reviews, minutes, edited reviews (P1's count), and DEFECT and STRENGTHEN counts;
- send-backs whose cause a planning review could have replayed (P2);
- implement-step reviews skipped by P4, and any defect found later in a skipped step.

## Questions for the advisors

1. Does P2's wording make a model actually replay, or only restate? What would make it compute?
2. Is P4's trigger (first step of the current plan, and changes source code) a real signal, or an artefact of 5
   defects in one domain (a chess engine)? Is there a better script-checkable trigger?
3. P3: are there send-back cases where a test-spec re-review is the only check that would catch a changed premise?
4. P5: is the end-of-work review the right place for surviving mutants, or should the test stage itself refuse an
   item with unexplained survivors?
5. Anything here that weakens a guarantee a later stage depends on?

## Panel outcome (2026-10-25, advisors run 20261025T211947Z-fadb)

**Who answered.**
- Pass 1: Astra (max effort) and Kimi. Opus hit its 100-turn limit; Grok refused `--effort max`.
- Pass 2: all four, at `xhigh` with 200 turns.
- Answers and synthesis: `docs/experiments/improve-schedule-panel-20261025/` (`final.md`).
- **Converged** on every disposition. This proposal is superseded by the rules below.

**What the panel changed.**
- **P1, keep as telemetry, re-specified.**
  - Hash the candidate under review, not `<action>-final-result.md`: the reviewer edits the inbox result in place,
    and the final-result file appears only at the parent return.
  - Record `tree_changed`, `result_changed` and `edited`; record missing evidence as unknown.
  - `metrics.improve_reviews` needs its own change. It never reads `passes.md`, and a one-pass review shows 0 s.
  - The stop threshold stays as it is. With one trivial pass required, `unchanged_first_pass` never decides.
- **P2, rewritten.** The central example was wrong. TC_28 was *added* by run 5b's test-strategy review and *replayed*
  there, with a helper whose docstring says "No legality". So the fix is validation, not replay: check each transition
  under the spec's rules, cover cases the review adds, and treat a helper that applies inputs unchecked as no
  validation. Put the text in the shared `PROCEDURE_WALK`, which already asks "can each action occur in the state the
  preceding actions leave", not in focus item 1.
- **P3, no skip; narrow the re-review to changed cases and their dependents.** Both of run 5b's re-reviews had
  changed cases (TC_28; TC_19), so the skip would have saved 110 s of the 344 s.
- **P4, shadow mode only.** Every later-step observation came from run 5b. Log "would skip" and keep reviewing.
  Adopt only the reuse of a review whose reissued step is unchanged.
- **P5, a disposition per in-scope survivor at the test stage**, then a reconciliation at end of work. Keep
  test-spec's weak-assertion focus.
- **P6, keep.** The count is 2 DEFECT, 7 STRENGTHEN, 1 POLISH, one DEFECT being a repair of the review's own earlier
  wording.

**Additions.**
- Count defects a review introduces, not only those it finds.
- Preserve result-only check evidence, which `_improve_pass` overwrites when the tree is unchanged.
- Fix the stale "two existing qualifying reviews" hand-off line.
- Log "would review" for unevidenced premises on later items (n=1).
