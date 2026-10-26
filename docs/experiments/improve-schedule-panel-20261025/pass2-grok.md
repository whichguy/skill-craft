Pass 1 produced no position, so I am checking the load-bearing disagreements between Codex and Kimi against the code and the run records before I adopt or reject them.The two seats disagree on whether P4 should ship and on what P2 actually failed to check. I am reading those code paths and the cited run files before taking a side.### 1. Hold

- Pass 1 emitted no claims. The seat runner exited before an answer. Nothing from that answer is held.
- Stance of this pass: ship P1 as telemetry only, replace P2 and P3, do not ship P4, pilot P5 as a test-stage disposition with an end-of-work audit, keep P6.

### 2. Augment / revise

#### ADOPT Codex (Astra):

- **Claim:** P1 records content identity, not "a final-result file exists." At bind and after each pass, store `tree_changed`, `result_changed`, and `edited` against the preceding candidate, using the frozen producer result as the baseline. Compare parsed result content. Missing evidence is `unknown`, not unchanged. At import, record separately whether the accepted result differs from the producer result. Do not change the stop rule because `edited` becomes true.
- **Why:** `metrics.improve_reviews` never reads `passes.md`. It counts `review-*.md` notes and sets seconds to last-mtime minus first-mtime, so a one-pass review reports 0 seconds (`test/shiploop_e2e/metrics.py` around line 955). The live stop is one trivial pass (`IMPROVE_TRIVIAL_REVIEWS = 1`; exit text at `shiploop_navigator.py` around line 8137: "at most trivial polish, committed"). Hashing only `run/inbox/<action>-final-result.md`, or treating file existence as an edit, misses an in-place inbox edit and can count a verbatim copy as an edit.

#### REJECT Kimi (K3):

- **Claim:** P1 must redefine `unchanged_first_pass` to "tree unchanged and result unchanged," and that this is required or result-only edits will keep closing after one pass while tree edits take a confirming pass.
- **Why:** With the gate at 1, a first trivial pass completes because `trivial_streak >= required`, whether or not the git tree moved. `until_loop_ephemeral.py` sets `unchanged_first_pass` only when that flag is true and the new streak is still below the required count. After a first trivial pass the streak is 1, and `1 < 1` is false, so the flag is not what ends the review. A second pass happens when pass 1 is classified non-trivial. Forcing the result file to be unchanged on the closing pass would forbid the trivial polish the exit condition allows. The import cross-check at `shiploop_navigator.py` around line 4457 only sees git paths, so inbox edits should be measured. They should not grow a new stop.

#### ADOPT Codex (Astra):

- **Claim:** P2 must require a valid transition, not a recomputed final state. Amend the existing procedure walk. Do not append "replay and record the replay" to focus item 1. Wording to use: "For each new or changed expected result derived from a sequence, validate the stated start and every transition under the specification rules, then recompute the result. Name the rule that permits each transition. Include examples this review introduces. Record the case ID, method or command, decisive intermediate states, computed result, and evidence location. A helper that only applies requested state changes does not show the sequence is permitted. Reuse earlier evidence only when its inputs, rules, and method still apply; otherwise leave the claim unresolved." Keep the obligation generic. Do not use "moves" as the example. Reuse a valid replay across spec, test-strategy, plan, step-plan, and test-spec instead of recomputing it five times. A short derivation is enough. The product under test is not the oracle.
- **Why:** Run 5b's test-strategy review already replayed `b2b4 b7b5 b4b5` with `apply_simple` and recorded exit 0 (`test-strategy-edacefd5/reviews/checks.md`). That function's docstring says "No legality" (`run/scratch/oracle_replay.py` line 50). The same review added `TC_28_promoFromStart` (`review-1.md`). That is a review-introduced illegal oracle, not a case nobody replayed. The walk P2 would duplicate was already in that review's handoff: "can each action occur in the state the preceding actions leave" (`handoff.md` lines 17–23). "Record the replay" and "paste the script output" are both satisfied by that failed check. The avoided send-back remains n=1.

#### REJECT Kimi (K3):

- **Claim:** P2 is fixed by requiring each intermediate state, a scratch script, and a `NOT-REPLAYED` mark, and the test-strategy replay is evidence that replaying pays.
- **Why:** The test-strategy pass did recompute intermediates with a script and pasted a matching FEN. The script does not implement the rules, so the illegal line was endorsed. A `NOT-REPLAYED` escape would not have fired. Citing the permitting rule is the part worth keeping. The script-output requirement is the failure mode.

#### ADOPT Codex (Astra):

- **Claim:** Replace P3's blanket skip with: "After a send-back, review the revised test spec's changed cases, affected dependent cases, and preservation of previously accepted requirements. Skip only when the script shows that a previously reviewed case contract and its relevant premises are unchanged. If no prior reviewed version exists, review it." Deleting the send-back clause of `_first_item_review` does not implement "initial test-spec only." That function is true for the first work item or any item with a send-back (`shiploop_navigator.py` lines 488–492), so W1 is still reviewed after every send-back.
- **Why:** The four cited re-reviews found nothing, about 344 seconds. The test-spec author writes the oracle, RED/GREEN rule, and procedure after the step-plan review (`shiploop_stage_spec.py` test-spec contract). A correct revised plan can still yield a wrong new expected value. "Five first-item reviews, all edited" mixes run 3's older per-item schedule with the later first-item rule. A verbatim row compare is not sufficient: a premise can change while the expected-result string is copied.

#### REJECT Kimi (K3):

- **Claim:** Skip the test-spec re-review when every case row keeps its ID and expected result from `spec_before`.
- **Why:** That check misses a changed premise or a weakened failure condition whose expected-result cell was copied. It is a useful script input to Codex's rule, not the rule. The step-plan re-review does not see case oracles the test-spec author adds afterward, which is the same gap Kimi named for derived FEN values.

#### ADOPT Codex (Astra):

- **Claim:** Drop P4 as the schedule. Keep it only as a "would skip" mark while every changed implement action is still reviewed. Replacement: "Review each changed implementation action. Reuse a completed review only when the candidate, the applicable contract, and the verification evidence are unchanged. A missing snapshot or an uncertain external-state change requires review. Step number and path class do not waive it." Reassess after ten further step reviews that include another domain and another step decomposition. Ten clean skips are not a safety threshold.
- **Why:** Run 3's cited implement packet is "Step S1 (1 of 1)" (`nav-aa400925…md` line 14). Run 5b has "Step S2 (2 of 6)" (`nav-341ebb44…md` line 14). Implement children on disk: run 3 has 4, run 4 has 4, run 5b has 14. Every later-step observation is one run. A reissued plan that repeats S1 and repairs S2 reviews the repeat and skips the repair. `path-classes.json` marks `.github/**` as config and permission-set metadata as `metadata-nav`, and both are `non_behavioural` for skipping a test stage, not for skipping review. The ask-agent route builds every step in one action (`step_scope` in `shiploop_navigator.py` around line 3518). The per-step tree is the step-entry snapshot (`_step_entry`, around line 4081), not a cumulative lint scope from the item base. The five defects do not identify a trigger that is safe outside this chess decomposition. n=1 for later steps.

#### REJECT Kimi (K3):

- **Claim:** Keep the first-step trigger and only stop excluding metadata and configuration; documentation and dotfiles may skip.
- **Why:** Narrowing the exclusion list does not fix the first-step conjunct. The repair-on-a-later-step case, the ask-agent one-action case, and the single-run later-step sample remain. Logging real skips does not recover a defect the end-of-work review never reaches. That review runs only when no work items remain (`shiploop_navigator.py` lines 481–485). Run 3 stopped before it.

#### ADOPT Codex (Astra):

- **Claim:** P5 is a test-stage disposition, then an end-of-work audit. Do not delete weak-assertion hunting from the test-spec review. Test-stage text: "For each current in-scope surviving mutant, name its candidate, mutation, and affected requirement. Add a behavioral test that passes on the unmutated candidate and fails on that mutant, or record evidence that the mutation is equivalent under the contract, outside product scope, or not exercised by this runner. Unresolved stays unresolved. Do not weaken the oracle or change required behavior to improve the count." End of work: "Reconcile outstanding dispositions with the final candidate. Recheck any disposition a later edit invalidates, and require execution evidence for a claimed kill." Refuse an unexplained in-scope survivor through that disposition. Do not require a 100% kill rate. Pilot the cost. Remote-only items stay skipped.
- **Why:** `mutation_check` refuses only when at least one mutant ran, none were killed, some survived, and remote commands were not skipped (`shiploop_mutation.py` around lines 405–418). Partial survival passes today. Run 3's record `nav-da24c1ff…-mutation1.md` includes survivors in `.sf/.../localSourceTracking/config`, so "kill every survivor" spends tests on tool state. Run 3 never reached end of work, and carry-forward review does not run while items remain. Sampled mutation also cannot replace the planning-time stand-in check. The proposal's "removing weak-assertion hunting from test-spec" must be struck.

#### REJECT Kimi (K3):

- **Claim:** The test stage must not refuse unexplained survivors, because equivalent mutants are judgment, a refusal reruns the item, and remote-only items cannot meet the guarantee. End of work is the only owner. A printed pointer line is enough.
- **Why:** The refusal is a missing disposition, not survival itself. Equivalence with evidence is an allowed disposition. Remote-only commands are omitted so they do not create survivors (`shiploop_mutation.py` lines 112–117), so there is no survivor those items must explain. A pointer does not bind a run that stops before end of work. The existing test-stage refusal path is the correction cycle. It is not a new Improve child.

#### ADOPT Codex (Astra):

- **Claim:** Keep the spec review. Do not price a STRENGTHEN at 36.8/8 minutes. The run 3 pass log has ten edited spec passes (passes 1–5 non-trivial, then two trivial), not the table's nine. Pass 5 fixed an ambiguous "h1h2 FEN" that "a correct engine would fail" (`spec-c4d005dc/reviews/review-5.md`). That is a DEFECT under the proposal's own definition, and it repaired wording introduced inside the same review. A defensible split is 2 DEFECT / 7 STRENGTHEN / 1 POLISH. Prioritize wrong oracles, missing observable behavior, contradictions, and requirements a later stage could falsely satisfy. Count producer defects separately from repairs of review-introduced defects.
- **Why:** I read `passes.md` and `review-5.md`. The 36.8 minutes include confirmation passes and self-repair, so they are not the marginal cost of one strengthening. Upstream oracle repairs feed every later stage. These runs support keeping that review. They do not price each pass.

#### ADOPT Kimi (K3):

- **Claim:** On later runs, record each spec-review STRENGTHEN and whether a downstream defect or send-back was avoided. Revisit only if several runs show none binding.
- **Why:** That is the owner's measured-gain rule applied to the review that costs the most per defect. It is a measurement, not a reason to drop the review now.

#### ADOPT Codex (Astra):

- **Claim:** Fix, independently of this schedule, the planning handoff line that still requires "the two existing qualifying reviews" (`shiploop_navigator.py` lines 7410–7412). The bound exit condition says "the qualifying review" (around line 8144), and the pass instruction was corrected on 2026-10-24 to one trivial pass (lines 7507–7510).
- **Why:** The stale sentence is still emitted for plan reviews. It can demand a second qualifying review the runtime no longer requires. No cited run isolates its cost, so the fix is consistency, not a claimed minute saving.

### 3. Still open

- I did not diff the four test-spec re-reviews case by case, so I do not know how many the conditional P3 rule would actually skip. The rule does not depend on that count.
- The minute and token cost of naming a permitting rule per transition, and of a survivor-disposition cycle, is unmeasured. The historical P3+P4 pool is on the order of 20 minutes across three runs, about 9% of Improve time, before any retained conditional reviews.
- A review of a new, unevidenced oracle or runtime premise on a later item is a plausible extra trigger. Run 5b's W2 send-back is n=1. Measure it. Do not add an always-on later-item review from that one case.
- Whether the stale "two qualifying reviews" sentence caused any extra pass is unmeasured.