All claims are now grounded. I verified the code paths and spot-checked the evidence on disk (run 5b = `/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d/.shiploop-runs/work-20261025-020942-4061a0`). Key confirmations and two findings the proposal missed are inline below.

---

# Verification summary

- **`_REVIEW_FOCUS_ITEMS` item 1** is verbatim what P2 quotes (`shiploop_prompts.py:794-796`) — it demands replay*ability*, never a replay. It feeds `REVIEW_FOCUS_CONDITIONS` → all `PLANNING_REVIEW_STAGES` reviews (`_improve_focus`, `shiploop_navigator.py:7166`) and the spec/test-strategy duty heads (`_duty_focus`, `shiploop_prompts.py:823`). ✔
- **"tree changed"** in pass-N.json is a pure git-tree-hash comparison (`pass_changed = tree != before`, `shiploop_navigator.py:8490-8497`), while a review's fixed result goes to `run/inbox/<action>-final-result.md`, outside the tree (`shiploop_navigator.py:3345`). P1's mechanism is confirmed in code **and on disk**: run-5b test-spec review `nav-6d9c61d3…` shows `tree changed: n` on a **non-trivial** pass while `inbox/nav-6d9c61d3…-final-result.md` exists. ✔
- **Re-review after send-back** comes from `_first_item_review` (`shiploop_navigator.py:488-492`): the "first-item" rule fires for the first work item **or any item with a send-back row**. `SEND_BACK_TO = "step-plan"` (`shiploop_stage_spec.py:71`), so every inner send-back re-runs step-plan and re-triggers its re-review. P3's "before" is exactly right. ✔
- **P3's run-5b numbers check out to the second**: the two cited re-reviews are `nav-5d572b10…264e1` (1 pass, trivial, n, **204 s** ≈ 3.4 min) and `nav-eec267e8…9e3f507` (1 pass, trivial, n, **30 s** ≈ 0.5 min). ✔
- **IMP-4's re-decision note** is printed in every passes.md header (`shiploop_navigator.py:8539`). ✔
- **Surviving mutants**: run-5b W3's record `run/tests/nav-9d5cc85f…-mutation1.md` contains multiple `"status": "survived"` mutants in `slChessBoard.js`; mutation records live at `RUN/tests/<action>-mutation<N>.md` (`shiploop_test_loop.py:135-137`); remote-target commands are deliberately skipped because "every mutant would survive and the check would refuse good tests" (`shiploop_mutation.py:112-117`). P5's facts and its "known gap" are confirmed. ✔
- **Two things the proposal missed in code** (details below): the one-pass fast-exit `unchanged_first_pass` is *also* tree-only (`shiploop_standalone_improve.py:647-650`), and the end-of-work review only fires when no work items remain (`shiploop_navigator.py:484-485`).

---

# Per-proposal verdicts

## P1 — count result edits, not only tree edits: **KEEP, with three amendments**

The claimed mismeasurement is real (verified above), and the fix is correctly framed as measurement-only. Three holes:

1. **Define "edited" by content, not existence.** The manifest's proxy "left `run/inbox/<action>-final-result.md`" happens to be sound today because `complete` forces `--final-result` only when a fix was made (`shiploop_navigator.py:3336-3348`; in run 5b, exactly the 9 reviews that fixed their result have one). But existence degrades into a false positive the day a model writes a verbatim final-result. Rule: *a pass counts as edited when the tree hash moved, or the final-result's content differs from the seed result it replaces.* Cost is one file hash per pass — as the proposal says — but hash both sides and compare.
2. **The fast-exit must join the new definition, or the count and the stop rule disagree.** The Until Loop closes on one pass "only when it saw the workspace unchanged (**Git tree**)" (`shiploop_standalone_improve.py:647-650`), and the restart gate refuses "one unchanged trivial pass [with] files changed since the bind" — files read from the git diff only (`shiploop_navigator.py:4457-4463`). Today a review can edit its result file in pass 1, be left at one pass, and record itself as "unchanged". If P1 fixes the count without fixing `unchanged_first_pass`, you get the measurement right and the stop rule wrong in the same place. Change the runtime's `unchanged_first_pass` to mean *tree unchanged AND result unchanged* — symmetric with how tree-editing reviews already behave (they take a confirming trivial pass; run 5b's editing test-spec review took 2 passes for exactly this reason). Median cost when it binds: one ~46 s pass. Under quality-first, take it — and note P1 thereby stops being "no behaviour change"; say so in the proposal.
3. **The pass log needs both columns.** Current rendering (`shiploop_navigator.py:8540`) prints one "tree changed" column; add "result changed" and have `metrics.improve_reviews` (`test/shiploop_e2e/metrics.py:955`) count a review as edited when either is "y" — for **every** producer stage whose product is an inbox result, not only the three named in the proposal (run 5b's spec, test-strategy, plan, and release-plan reviews also left final-results, so the tree-only count mismeasures them too).

## P2 — the planning review replays derived expected values: **KEEP, with stronger wording**

The diagnosis is precise and verified: item 1 asks for replayable examples, never a replay, and the one escaped case (TC_28, b2b4 b7b5 b4b5 — illegal, the b5 square is occupied after …b7b5) cost a full deploy+send-back cycle. That escape is **n=1**, but the supporting direction is stronger than the proposal admits: the two times reviews *did* replay (run 3 spec review, run 5b test-strategy review) they found errors. The observed evidence is "replaying pays twice in three runs, skipping cost one send-back" — not "one miss in three runs".

The proposed wording has the flaw the advisors' question anticipates: "replay … and record the replay" can be satisfied by a fabricated trace. Three additions make restating visible and computing cheap. Replacement item text:

> an expected result derived from a sequence of inputs (user actions, calls, data writes): replay the sequence from its start state under the spec's own rules, recomputing each intermediate state and naming the rule that yields it, and record the replay in the review file; where the derivation is mechanical, recompute it with a short script in the review's experiment scratch and paste its output. If you did not recompute a result, mark it `NOT-REPLAYED: <reason>` — never record a replay you did not perform.

- The per-transition rule citation is what catches TC_28's error ("b4–b5: illegal, b5 occupied") — a global pattern-match over the line does not.
- The scripted route exists already: `.shiploop-improve/.experiments/` and `references/planning-experiments.md` (`shiploop_navigator.py:8560-8569`). Pointing there makes computing the path of least resistance rather than an extra demand.
- The explicit `NOT-REPLAYED` exit is the honesty lever: models bluff when the only available move is to claim success.
- Keep "(moves, calls, records)" out — "moves" reads chess-flavoured and stacks the deck against the generic-focus rule; the parenthetical "user actions, calls, data writes" covers the same ground.

This one item propagates everywhere it should with no extra work: it rides `_REVIEW_FOCUS_ITEMS` into `PLANNING_REVIEW_FOCUS` (all seven planning-stage reviews) and into the spec/test-strategy duty heads. The +~300 characters against the 20,000 cut (spec head 14,354) is fine under the standing policy of raising a bound rather than trimming obligations.

**Measurement to add:** count reviews with at least one recorded replay and reviews with `NOT-REPLAYED` marks on the next runs. That is the only way to know P2 changed behaviour rather than prose — per your own "test the route, not the wording" principle.

## P3 — no test-spec re-review after a send-back: **CHANGE — skip only on a verbatim carry-over**

The evidence (4 of 4 re-reviews unedited; I verified two of them to the second) is real but **n=4 across send-backs that changed very little**, and the blanket rule weakens two guarantees at exactly the moment they matter most:

- **Row integrity on revisit.** The revisit head instructs "Keep unchanged rows with their IDs" (`shiploop_navigator.py:875`), and the known failure mode is recorded one comment away: "a redone test spec searched the run for its own earlier result and resubmitted it unchanged" (`shiploop_navigator.py:708`). Focus item 5 ("a required requirement, test ID or case dropped or weakened compared with the prior accepted version") is the only review-side guard on that, and the blanket skip removes it precisely when a rewrite has happened.
- **Anti-synergy with P2.** Run 5b's send-back was caused by a wrong derived sequence; the fix itself derived new expected values (rewritten S3, new expected states). Under P2+P3-blanket, those new derivations are replayed at the step-plan re-review only if they live in the plan — but derived *expected values of cases* live in the test spec (as the TC_4/TC_8 FEN recomputations show), and no remaining review would replay them.
- The saving is the smallest of the six: ~1.9 min/run average.

The trigger the proposal should use instead is script-checkable with machinery that already exists — `_sent_back_results` already surfaces `spec_before` (`shiploop_navigator.py:717-754`):

> After a send-back, skip the test-spec re-review only when the redone test spec carries over every case row with its ID and expected result unchanged from the item's spec before the send-back. A changed, added or dropped case row keeps its review. The step-plan re-review after a send-back stays in every case.

That removes exactly the 4 no-op reviews you measured if they were verbatim carry-overs (check before committing to the number), and keeps the review wherever the premise actually moved. If you want the simpler blanket rule anyway: it is the weakest of the six proposals and I would take it only with the "defect found later in a skipped review" counter-metric armed.

## P4 — review an implement step only on first-step-of-current-plan that changes source: **CHANGE — tighten the exclusion list; keep everything else**

The behaviour claim ("no DEFECT in these runs would be lost") is internally consistent: all 5 defects sat on first-step-and-source steps, which keep their reviews; I verified the end-of-work review's current focus covers whole-app tracing (`IMPLEMENT_STEP_REVIEW_FOCUS_HEAD` and `END_REVIEW_FOCUS_HEAD`, `shiploop_prompts.py:2541-2571`). Both trigger conditions are script-feasible: `_step_plan` resolves the latest accepted plan per item (`shiploop_test_loop.py:294-302`), per-step changed paths come from `changed_since` against the review base (`shiploop_item_scope.py:148-150` — already used by the improve opening at `shiploop_navigator.py:8594-8595`), and the linter's per-file kind classification exists.

The problem is the exclusion list, and this very domain is the counterexample: on a metadata-driven platform the "metadata" files *are* the behaviour — object, permission and UI declarations, not inert config. P4's own evidence concedes the shape of the loss: one defect's second half ("all squares one colour; the page was never opened") is invisible to every remaining check — and a metadata-only step that deploys UI is exactly where such defects live. Under quality-first, "0 of 12 found anything (n=5 defects, n=3 runs, one domain)" does not pay for excluding the layer where behaviour is declared. Replacement rule:

> A step gets a review when both hold: it is the first step of its item's current step plan (a re-issued plan included); and its changed files are not all documentation or dotfiles.

i.e., delete *metadata, configuration* from the exclusion list. Yes, this saves less than 15.9 min across the three runs — the proposal cannot tell us how much less, because the 12 skipped reviews lump "later steps" with "metadata/config only" and the two conditions are fully confounded in n=5. Keep the rest as proposed: the IMP-4 re-decision gate (already printed in passes.md at `shiploop_navigator.py:8539`), and — strengthen it — log each skipped step review in passes.md so "defect found later in a skipped step" is countable next run instead of anecdotal.

Also fix one false safety sentence in the proposal: "The end-of-work review stays for every run" is not a guarantee — it fires only when no work items remain (`shiploop_navigator.py:484-485`), and run 3 never reached it. P4 as amended doesn't depend on it (all 5 observed DEFECTs were on first steps), but the rejected "drop all per-step reviews" variant would have, so keep it rejected.

## P5 — end-of-work review reads surviving mutants: **KEEP as a pure addition; strike the removal clause**

Verified: survivors exist and were never dispositioned (run-5b W3's record on disk), and remote-only items legitimately produce no records (`shiploop_mutation.py:112-117`). The end-of-work review is the right place (see Q4). Two fixes:

1. The sentence "removing weak-assertion hunting from test-spec" reads as deleting focus item 3 from the test-spec review. If meant literally: **don't.** Item 3 is what produced 5 of test-spec's 6 editing passes, including run 4's "TC_1 would accept TC_10" fix — a stand-in-oracle catch made *before code exists*, which is the only time it's cheap. Mutant survivors are the end-review's *additional, evidence-backed* instance of the same condition; reword to "pointing the end-of-work review at real survivors puts evidence behind the condition the test-spec review checks blind." If the clause wasn't meant literally, delete it anyway — it's ambiguous in a document that otherwise names precise edits.
2. Implementation notes: read the **latest** mutation record per action (records are numbered and re-run after fixes), and note that the end-of-work review only runs for runs that finish with an empty queue — a stopped run (like run 3) leaves survivors undecided either way. Cheap complement worth adding now: when a test stage's done leaves unexplained survivors, print one pointer line ("N mutants survived, see RUN/tests/…-mutation1.md; the end-of-work review must kill or justify each") so the obligation is visible at the point of creation rather than discovered at the end.

## P6 — spec review stays: **KEEP, and answer the open question with a binding test**

Yes, ~4.6 min per spec-level STRENGTHEN is worth it *if* those STRENGTHENs are load-bearing, and the evidence says they are: 7 of 8 editing passes made oracles stricter that every later stage (test-strategy → cases → proofs) inherits, and this is the layer F1–F6 exist to defend, with run 4's TC_1-accepts-TC_10 as a live example of what slips when a stand-in survives. The honest way to keep this decision evidence-based rather than faith-based: record each spec-review STRENGTHEN and check on subsequent runs whether any prevented a downstream defect/send-back. If after the next few runs none ever bind, revisit — that's the measured-gain rule applied to the reviewers, not just to the reviewed. Separately, 36.8 min for 3 reviews (~12 min each) is worth one look at pass composition: the figure is quoted per DEFECT but the review isn't expensive *because* it finds defects; check tokens-per-pass before concluding anything from the ratio.

---

# The five questions

**1. Does P2's wording make a model replay or restate?** As proposed: it licenses restating, because "record the replay" accepts a fabricated trace. What makes it compute: (a) require the intermediate state after *each* input with the rule that yields it — pattern-matching can't produce that cheaply, computing can; (b) give an explicit `NOT-REPLAYED: <reason>` exit so honesty is an available move; (c) route mechanical cases through a script in the existing `.experiments` scratch so computing is less work than fabricating. Even then you get auditability, not certainty — a fabrication becomes checkable evidence, and `NOT-REPLAYED` counts become a metric. Use my replacement text under P2.

**2. Is P4's trigger a real signal?** Partly. The mechanism story is plausible and domain-general — the first step of a (re)plan is where the item's core semantics land (all 5 defects are of that kind: parser acceptance, board indexing, stale state), and later steps build on an already-exercised base. But "first step" and "changes source" are confounded in n=5 defects / n=3 runs / one domain, so the data can't rank the two conditions. I found no better *cheap script-checkable* trigger: "step adds an untested public entry point" isn't cheaply detectable generically, and diff-size is a bad proxy (the run-3 defect was a one-character class of bug). Keep the pair with the tightened exclusion (docs/dotfiles only), the re-decision gate, and a skip log.

**3. Send-backs where only a test-spec re-review catches a changed premise?** Yes, two: (a) the redone spec *derives new expected values for changed rows* — derived values live in the spec, and the step-plan re-review never sees the derivation (run 5b's own FEN recomputations happened in a spec review); (b) a case row silently dropped or weakened on rewrite — the revisit head commands carry-over, but nothing enforces it except focus item 5 in a re-review. Both are why my P3 replacement keys the skip on a verbatim carry-over instead of dropping it.

**4. Should the test stage refuse items with unexplained survivors?** No. Survivors can be equivalent mutants (judgment, not a gate); a refusal would rerun a whole item for one missing assertion; and remote-only items skip mutation by design, so a refusal would create a guarantee some items structurally can't meet — uneven rules invite exactly the dodge you're trying to prevent. The end-of-work review is the right place: it batches all items' survivors, already has fix-with-test authority ("each fix comes with a test that fails before it", `shiploop_prompts.py:2549`), and can record "cannot be killed" justifications. Keep P5 as written (addition only).

**5. Anything weakening a downstream guarantee?** Three, already covered: P3-blanket removes the row-integrity and derived-value checks at the one moment a rewrite occurred; P4's metadata/config exclusion removes the only review of behaviour-declaring files on metadata-driven stacks (and its safety net, the end-of-work review, doesn't exist for stopped runs); P5's ambiguous clause would remove the planning-time STRENGTHEN layer if read literally. P1 and P2 weaken nothing; P1 done right *strengthens* the stop rule.

---

# What the proposal missed

1. **`unchanged_first_pass` is tree-only too** (in P1 above) — the stop rule and the new count will disagree unless fixed together. This is the single most important correction: without it, P1's numbers will keep understating edits *and* reviews that edit only their result will keep ending after one pass as "unchanged".
2. **A skip log for P4**: record each skipped step review (step id, why skipped) in `passes.md` or a sibling record, or "defect found in a skipped step" — the re-decision input for IMP-4 — stays unmeasurable.
3. **P2 needs a behaviour metric**, not just a cause metric: "reviews with a recorded replay" / "`NOT-REPLAYED` marks" on the next runs. Without it you cannot tell P2 worked — same standard you applied to P1's own miscount.
4. **P3's saving claim should be re-stated after the conditional fix**: verify the 4 no-op re-reviews were in fact verbatim carry-overs; if any changed a case row, it doesn't disappear under my rule and the blanket version's "2 minutes, nothing lost" is already wrong on the existing data.
5. **The cheap survivor pointer at test-stage done** (in P5): one printed line closes the "silent survivor" hole without touching any gate.
6. **Run-3 legacy cost in P4's savings number**: run 3 predates the one-unedited-pass rule, so some of the 12 skipped reviews' minutes include the old two-pass confirming cost; on current rules the realised saving will be under 15.9 min across three runs. Doesn't change the verdict; does change the expectation to set with the owner.

**Bottom line:** keep P1, P2, P5, P6; change P3 (verbatim-carry-over condition) and P4 (docs/dotfiles-only exclusion, plus skip log). Before landing, make the two mechanism edits the proposal missed: `unchanged_first_pass` joins the result-file definition, and P3's condition reuses `_sent_back_results.spec_before` instead of a new blanket rule.