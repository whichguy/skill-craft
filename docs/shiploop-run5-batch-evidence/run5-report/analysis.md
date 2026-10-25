## Verdict

**Run 5b is the first chess run to pass end to end.** ShipLoop reached `done` and handoff in 284 active minutes, and all
five checks passed:
- `project`, `deployed` and `committed` passed, where runs 3 and 4 failed them;
- `tests`: 27 Apex tests ran, none failing;
- `rules`.

Every release stage ran, 6 of 6; runs 3 and 4 ran 0. This shows that the 2.9.0 gates held in normal use, not that the
run was cheap: re-orientation and Improve time are still the largest costs.

The first attempt, **run 5a**, was blocked after 93 min at W1 implement for a reason outside ShipLoop. The Grok host had
moved from 1.0.62 to 1.0.70, and its auto mode refused `sf project deploy start --target-org de` as "a remote
stateful mutation"; run 4 had sent that command shape 15 times under the same allow rules. ShipLoop reported `blocked`
rather than faking a deploy. Run 5b used `--permission-mode bypassPermissions`, the owner's choice; the harness's sf
guard still kept all 232 `sf` calls inside org `de` and the SLChess prefix.

## Ranked findings (newest first)

| # | Finding and evidence | Proposed change | Minutes at stake | Where |
|---|---|---|---|---|
| 1 | **Re-orientation is the largest cost: 125.2 min and 1,169 calls over 21 compactions** (run 4: 74.0 min, 15). Part of it is the resume after the sleep, but the rest is the 10-step, 3-item queue rereading its packets. | Bounded heads and template-rendered packets (slice 4), then re-measure. Count re-orientation separately for each resume. | ~60-125 | slice 4 (deferred until this measure) |
| 2 | **Improve: 27 reviews, 41 passes, 83.8 min** (run 4: 13, 25, 81.8; run 3: 16, 52, 98.9). There are more reviews because each of the 10 steps has one; passes per review fell to at most 3. The spec review added real stand-in oracles (5a: 7 passes; 5b: 3), and the end-of-work review found two real board bugs. | Keep. Measure value per pass, not the count. A per-step review of a tiny step is the candidate to skip. | ~20-30 | outside the plan |
| 3 | **Prepare's `harness_runs` gate checks only that an evidence file exists.** In 5a the evidence was a browser probe page saying "This is not … the slChessBoard component"; in 5b it was a real jest run ("1 passed"). | Require a test-result line in the evidence (a count, pass/fail, ok/not ok), plus a known-dodge row. | small, but closes an F1 hole | next batch |
| 4 | **Two implement steps found a criterion they could not meet and sent back** ("C28's promotion line needs an illegal straight pawn capture"; "C6 cannot be caught from anonymous Apex"). The route worked; each send-back cost about 6-10 min of rework, and W1's full cycle was 109.6 min against 51.8 and 53.3. | Have the step-plan review (or a gate) check that each criterion is reachable by its planned command before implement. | ~15-20 | next batch |
| 5 | **`primary` does not discriminate:** 5a marked 7 of 7 requirements primary, 5b 13 of 14. F6 then held without add-work, because component and Apex tests backed both unobserved primary outcomes. | The spec placeholder and duty say that primary outcomes are what the user asked for directly, usually a few. | low | next batch |
| 6 | **After a mid-item send-back, expectations are still judged against the item's original base.** The refusal "expectation E3 is works, but …SLChessEngine.cls does not exist on the item's lint base" made the model call an existing file absent. | Judge a revised step plan against the latest step commit, or say so in the refusal. | small | next batch |
| 7 | **Mutation coverage of the Apex code is zero by construction:** W1 and W2 were skipped as all-remote. W3's component tests killed 6 of 8 mutants. | Accept, since a checkout mutant cannot reach the org, and report it as a known gap. An org-side mutation pass is a later option. | n/a | outside the plan |
| 8 | **Environment variables decided two outcomes:** the Grok host update (5a blocked), a mid-run Homebrew Python swap (5a crashed at its end) and a 9.8 h sleep (5b's wall-clock cap spent at 229 active min). | Released in v2.9.1: run deadlines count active time (`time.monotonic`), `_strptime` is loaded at start. Record the host build per run, and treat a change as non-comparable (the E2E scorecard does). | n/a | harness |
| 9 | **Retired terms still printed in refusals:** "run the same complete command again", and "whose consumer is". Each phrase was split across two string literals, so the line scan missed it; the run's `nomenclature` record caught one. | Released in v2.9.1: all 7 leftovers fixed, and the retired-terms suite now reads the strings a script can print. | n/a | released in v2.9.1 |
| 10 | **F5's regression-line check is weak on extra tokens:** `TC_B4_promotionQueen (b)` passes because "(b)" occurs in almost any test file. | Check only ID-like tokens. | low | next batch |

## Test quality (the run's own records)

| Measure | Run 5b | Reading |
|---|---|---|
| Executed criteria confirmed only by a grep of code | **0** | F1's gate held: a grep-only "executed" check is refused at step-plan |
| REDs faked by a file guard | **0** | F2's guard gate held |
| Criteria confirmed by inspection | **0** | nothing was left to "inspection suffices" |
| Greps for a searched criterion (the docstring duty) | 6 | context, not dodges |
| Mutation check | W3: 6 of 8 mutants killed; W1, W2: skipped (all-remote) | component tests are strong; the Apex code goes unmeasured by mutation |
| Gate refusals, each caught in stage | producer limits 3, spec write-back 1, expectations 1, assumption link 1, other 3 | 9 fired, 9 caught, none repeated |
| Primary outcomes left unobserved | R-10 (play on the board) with `TC_B1_startBoard`; R-9 with `TC_19_controllerMates` | F6 held, with no add-work |
| End-of-work fixes with a regression test | 2 of 2 (`TC_B4_promotionQueen`, `TC_B6_newGame`) | F5 held |

## What changed since run 4, observed

- **F1 test layers.** The board's component layer became prepare work, and 5b proved it with a real jest render test.
  5a's dodge shows the evidence check is still needed (finding 3).
- **F2 file guards.** No guarded focused command in either run.
- **F3 targets and I2 remote base run.**
  - Org `de` is recorded as a target that keeps state.
  - W1's base run left both Apex commands out as remote, with F3's reason.
  - Verify printed "RED unobserved".
  - Run 4's W2 send-back, caused by a remote test on a base that already held the change, did not recur.
- **F5 regression line.** Both end-of-work fixes named their test, and nothing was refused.
- **F6 primary outcomes.** Product-acceptance accepted the unobserved board outcome only with a passing component
  test, so run 4's "accepted on words" failure is closed.
- **Step size.** The producer limit refused W1's single step, whose criteria totalled 5,192 characters. The model split
  it into 6 behaviour steps, each committed with a lesson. Improve commits cited earlier commits 12 times out of 13
  (run 4: 6 of 11).
- **Release stages.** 6 of 6 ran, against 0 in runs 3 and 4.

## Still open

- Re-orientation (finding 1) and slice 4, which waits on this measure.
- Findings 3-6 and 10, for the next batch.
- Cost is a lower bound ($21.65, turns 1,265): segment 1's Grok session ended in the sleep without writing its
  cost. Run 5a, the blocked first attempt, cost about $25.5 more.
- The app is kept in org `de` (`--keep-platform`, owner decision 2026-10-17). The next chess run's preflight refuses
  until it is removed with the case's cleanup command and this run's `platform/before.json`.

## Where the build plan stands

- **Slice 1** (outcomes, symbols, loop texts): shipped in 2.6.0-2.7.0.
- **Slice 2** (plan data and producer bounds): shipped in 2.8.0. The step bounds drove 5b's W1 split.
- **Slice 3** (the implement record: step commits, write-back, revisit): shipped in 2.8.0. Step commits carry lessons,
  and the spec write-back gate fired and held.
- **Slice 4** (templates): S4.4 shipped in 2.8.0. The engine, slots, templates, registry and ledger (S4.1-S4.3,
  S4.5, S4.6) are deferred, and this run's 125 min of re-orientation is the measure they target.
- **Outside the plan, in this release:**
  - 2.9.0: F1, F2, F3, F5 and F6, the I1-I3 fixes, the four renames (R1-R4) and the dodge table;
  - 2.9.1: the leftover retired terms, the active-time deadline and the Improve review counter.
