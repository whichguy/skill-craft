# F31 live check: implement's exit condition names the Proof (registered 2026-11-01, before any run)

Owner, 2026-11-01, answering "Take up F31 with a pre-registered live check?": "Yes, take it up".

Decision record, before any run: at 13:48 another session recorded the owner's "Yes, leave it" for F31
(a032bb167552bc867ae22a21f31847cdbd514554). Asked "Which of your two F31 answers should stand?", the owner answered "Run the live
check". That session's evidence is in docs/experiments/implement-send-back-class-20261101/. In 20 runs of shared-expenses, the Confirm-by
reading caused 1 of 6 implement loops, each loop cost about 2 minutes, and every loop recovered. The design below is unchanged.

## What F31 is

Planning journal F31 (entry E20; docs/shiploop-step-plan-review-2026-11-01.md §7a and §8, item 4). Implement reads a
criterion's Confirm-by test as due at implement, although the test stage writes that test after implement, and it sends
good plans back. There are three live cases:
- FX F ticket-import s1 (2026-10-31): "C1 and C2 require a new test file which the implementation contract forbids
  writing until test stage". Its Proof was `npm test`. Rule C (skill-craft 2.27.4) now refuses that plan at step-plan.
- XI B ticket-import s4 (2026-10-31): "C2 requires focused test execution during implement, but implement forbids
  writing those tests and test is a later stage". Its self-contained Proof and the 117 existing tests had passed.
- SP1 xhigh csv-report s1 (2026-11-01, ShipLoop 1.27.0), the second send-back: "C1-C3 still require confirmation by
  unittest cases TC_1-TC_3 ... A passing scratch proof is not the literal specified confirmation". Its real Proof had
  passed.

The cause, read from the source:
- Implement's first exit condition (`shiploop_stage_spec.STEP_CRITERIA_CONDITION`) asks that each criterion be "shown by
  a command or file after the last edit". The criterion's own text names its Confirm-by tests, and implement's duty says
  "Write no tests".
- The planning guide said implement "loops until each is confirmed" (references/backchain-planning.md). That sentence is
  from f7d29e31 (2026-09-24), before each step got its own Proof (12151c49, 2026-10-17).

## The change (arm B)

- `STEP_CRITERIA_CONDITION` now reads: "... shown after the last edit by the step's Proof or another command or file
  (tests named in a criterion's Confirm by are written and run at the test stage), ...". It is the first exit condition
  of every implement Until Loop, on both routes. It adds 106 characters to implement's head and whole text (inline head
  17,041 and ask-agent head 17,219 at the reference install; the cut is 20,000).
- references/backchain-planning.md: implement loops until the step's Proof confirms each criterion, and the test stage
  writes and runs the tests a `Confirm by:` names.
- A route test in test/shiploop-test-loop.test.py,
  `test_implement_done_rests_on_the_proof_while_the_criterions_confirm_by_test_is_unwritten`. The step's contract carries
  the condition, and `complete` accepts implement's done on its Proof with the Confirm-by test absent. It fails on the old
  wording.
- Change note changes/shiploop/implement-proof-shows-criteria.md (patch), and the two head tables (implement only).

Arm A is this registration commit. Arm B is the candidate commit on branch `exp/f31-implement-proof-bda511` whose parent
is this commit. Its patch-id (`git patch-id --stable`) is f867fa0a9e5129c91e680f3767be2cac80d5d7ed, so a rebase keeps it identifiable.

## Design

Subject: Codex `gpt-6.1-terra` at xhigh (the owner's runner), all tools, `--permission-mode auto`, with ShipLoop built
from each arm's checkout. `launch.sh` in this folder runs everything, at most 5 at once, into
`~/e2e-runs-f31/20261101/<arm>-<case>-s<n>`.

- **Part 1, mechanism: 16 slices.** `test/shiploop_e2e/slice.py --seed-at test-spec --stop-after implement` on
  tickets-assign and stand-in-rules, 4 per arm per case, in the order A B B A A B B A for each case.
  - Each case's seeded step plan is used unchanged. Every criterion reads "Confirm by: the focused command; pass when
    TC-<n> passes". The focused command runs a test file the test stage writes later, and step S1's Proof runs the
    behaviour directly (`node -e` with assertions).
  - So every slice puts implement where F31 happened: a good Proof, and criteria whose Confirm-by tests do not exist
    yet. Test-spec and validate-existing run first, as in a delivery.
- **Part 2, no harm: 6 deliveries.** `test/shiploop_e2e/run.py --case csv-report`, the case where F31 last happened
  live, 3 per arm, in the order A B B A A B.

## Measures (`score.py`)

- **F31 send-back.** An implement send-back that says a criterion's confirmation (its Confirm by, or the criteria's
  tests) needs a test that implement may not write, that does not exist yet, or that the test stage writes. A send-back
  that blames only the step's Proof needing an unwritten test is the proof-order class, not F31.
  - `score.py`'s pattern lists candidates.
  - Every implement send-back is labelled from `score.py --blind` into `labels.jsonl`, with the reading quoted. That list
    shows the headline and summary only, shuffled, with no run or arm, and the labels are made before the scores are
    joined.
- **Tests written at implement (slices).** A test file among the candidate's changed paths after implement. A slice
  stops before the test stage, so any test file there is implement's.
- **Checks (slices).** Every case check exits 0 on the candidate.
- **Delivery pass (Part 2).** run.py's verdict: every hidden check passes.
- **First-try done (slices).** The item's first implement result is done.

## Decision rule

Adopt (merge to main and release) only when all four hold:
1. Arm B has no F31 send-back.
2. Arm B writes no test at implement.
3. No harm: B's slices pass their checks at least as often as A's, and B's deliveries pass at least as often as A's.
4. Every run finished, and every candidate send-back is labelled.

The benefit is A's F31 count. If A has none, the mechanism is unexercised and the benefit unmeasured, as with fix 1
(journal E15 and E16). The change is then adopted on 1 to 4 alone, because it states what the gate already does: at
implement's done, ShipLoop runs only the step's Proof. It also removes a contradiction that implement itself named.

If 1 or 2 fails, the change is not adopted and the branch stays off main. If 3 fails, every failing run is read. The
change is adopted only if each failure is shown to be unrelated to it (infrastructure, a port, a host timeout).

Power: there are 8 slices per arm. If A's F31 rate were 10% per slice, A would show at least one 57% of the time; at
30%, 94% of the time.

## Amendment (2026-11-01, before any score)

Made on evidence from another session, Prompt enrichment research (docs/experiments/implement-send-back-class-20261101/;
runs in ~/e2e-runs-r3/20261101, Codex Terra 6.1 high, a greenfield Node case). When it was written, no run of this check
had finished and nothing was scored. The definition of an F31 send-back and the decision rule are unchanged.
- **Power, recalibrated.** That study had 28 implement attempts with a direct-probe Proof whose executed criteria named
  test-stage tests in their Confirm by. They gave 1 F31 send-back (3.6%) and 27 done. At that rate, 8 slices show at
  least one F31 in arm A only about 25% of the time. So "mechanism unexercised, benefit unmeasured" is the likeliest
  outcome, and the decision then rests on rules 1 to 4. The 10% and 30% figures above were assumptions.
- **Labelling shows the Proof.** 5 of that study's 6 implement loops also named the unwritten TC tests, but their Proof
  was the test runner on a base with no tests (`node --test`, or a wrapper naming the test file). That is the
  proof-order class, which arm B's wording cannot fix. A label made from the headline and summary alone could call them
  F31. `score.py --blind` now also prints the Proofs of the step plan in force at each send-back, still without its run
  or arm, so the registered definition can be applied. In Part 2 step-plan writes its own Proofs, so such send-backs can
  occur in either arm.
- **A clean F31 to calibrate the labels:** that study's A10, second send-back. "S1 independent HTTP proof passed, but
  C1-C3 still require unwritten TC_1-TC_4 at implement stage, which prohibits test creation."
- **Cost anchors:** a loop averaged 2.0 minutes (1.1 to 3.2, n = 6), and F31 was 1 of the 6 loops, about 0.1 minutes a
  run in that case. The no-harm rules weigh more than the benefit.

## Result of round 1 (2026-11-01): adopt by its rule, but the first wording is not merged

All 22 runs finished (`scores.json`, `labels.jsonl`; runs in `~/e2e-runs-f31/20261101`).
- **Slices.** A 8 of 8 and B 8 of 8 had implement done on the first try, every case check passing and no test file
  written.
- **Deliveries.** csv-report passed every hidden check in A 3 of 3 (10.0, 11.5, 13.7 minutes) and B 3 of 3 (13.4,
  10.2, 13.9).
- **Send-backs.** There was one implement send-back in 22 runs, in B csv-report s3: "S1 proof runs unittest before any
  test exists ... Replace proof with a meaningful standalone CLI check". Its step's Proof was `python3 -m unittest -v`
  on a base with no tests. Three independent labellers, shown only the text and the Proof, labelled it proof-order,
  3 of 3, so it is not F31. The labelling was not blind at the arm level: this session had already seen the unlabelled
  scores.
- **The rule.** Arm A had no F31 send-back, so the mechanism was not exercised and the benefit is unmeasured. The
  amendment had named that the likeliest outcome. Rules 1 to 4 hold, so by its rule round 1 says adopt.
- **Apparatus.** The first launch's six deliveries were refused before starting: the finished slices' observers were
  still running, and run.py's lifecycle check refuses a launch while they do. `lifecycle.py cleanup` on each slice
  folder stopped them. The six relaunched in the registered order four minutes later, with no delivery started before
  the refusal and no slice rerun. The refused logs are kept as `*.refused-1.log`, and the first launch log as
  `launch-1.log`.
- **Scorer bug, fixed.** The first scorer counted an unread arm-B candidate as a rule-1 failure, where the registered
  rule calls the result incomplete. `score.py` now reports incomplete until every candidate is labelled.

The first wording is not merged. An adversarial review of the candidate and the decision (workflow wf_a1a6868f-25f:
three lenses, each material finding put to a skeptic) found three problems that no verifier could refute:
1. **It breaks a full-tier test.** `test/shiploop-callback-contract.test.py`,
   `RefusalRouteTests.test_the_implement_packet_does_not_ask_for_a_field_the_accepted_plan_does_not_hold`, asserts that
   implement's Done-when never names `Confirm by`. That is 84d4d9da664dfb21b9f842179489ad32a03fefca: an item without
   tests has no criteria and no Confirm-by text. The quick tier with `--changed-from` does not select that suite for an
   edit to `shiploop_stage_spec.py`.
2. **It lets a Proof that exercises nothing stand as the witness.** Rule C accepts a plain suite Proof whose Confirm by
   names its test by ID, or in an existing file. At implement no script checks the first condition, and the first
   wording told implement that "the step's Proof" shows the criterion. The old wording did not require an observing
   command either.
3. **SKILL.md still contradicts it.** Its procedure item 2 still said "confirm each by its stated method ... route to
   planning", the reading behind F31, and an inline implement has the card in context.

## Amendment 2 (2026-11-01): the revised wording and round 2, registered before any run of it

Arm V, the revised candidate, is commit cb558e6367c2a4b1d05268afa70f5ff0bad46ef5 on `exp/f31-implement-proof-bda511`,
patch-id d15a5b730c444a149ac8fe0264b3efdf6eda380f. It is the third commit on the branch:
- 97667d22 is the first wording, which round 1 ran.
- 2e2240dd revised it after the first review.
- cb558e63 fixed what a second review of 2e2240dd found:
  - a "; " inside a done_when entry, which shiploop-stage-spec forbids;
  - "a check in RUN/scratch", which names a symbol the contract does not define and a location outside implement's
    scope;
  - no route for an inspected criterion;
  - a stale change note and an unjournaled table.
  2e2240dd never ran live.

V's first exit condition reads "... shown after the last edit by a command or file that observes it (for an executed
criterion, the step's Proof where it exercises the criterion, else a command of your own that runs the behaviour, since
a criterion's own tests are written and run at the test stage), ...".
- It names no result field and holds no "; ".
- SKILL.md item 2 and references/backchain-planning.md say the same.
- Implement's head and whole grow 217 characters against main, on both routes.
- The route test pins the wording, and stage-spec and callback-contract pass on it. The full shiploop, core and
  e2e-apparatus groups run locally before merge.

Round 2 uses the same subject, the same settings and arm A (this folder's registration commit), and runs `launch2.sh`
into `~/e2e-runs-f31/20261101-r2`. It stops each run's observers when the run ends.
- **Part 3, the hollow Proof: 12 slices.** tickets-assign, seeded at test-spec and stopped after implement, with
  `--seed-records hollow-proof-seed.json`. That file replaces S1's Proof with `npm test`, which passes on the base's
  existing tests and exercises none of the step's criteria; the criteria and the rest of the seed are unchanged. 4 per
  arm for A, B (the first wording, 97667d22) and V, in the rotated order the launcher lists.
- **Part 4, V's no-harm runs: 11.** Arm V on the round-1 seeds (4 tickets-assign, 4 stand-in-rules) and 3 csv-report
  deliveries. They are compared with round 1's arm A.
- **The hollow measure.** For each implement action of a hollow slice, `score.py --blind` shows the notes implement
  wrote (RUN/notes/<action>.md), the Proofs in force and the outcome, shuffled, without run or arm. Each is labelled
  `observed` or bare.
  - Observed: the notes record a passing check, beyond the Proof and lint, that exercises one of the step's criteria
    (an HTTP or assertion check, or a RUN/scratch script), or implement sent the hollow Proof back.
  - Bare: done with only the Proof (or the existing suite) and lint recorded.
  - Labels go in `labels.jsonl`, keyed as `score.py` prints them, made by three independent labellers shown only that
    list.
- **Rule (`score.py --round 2`).** Merge the two candidate commits and release only when all five hold:
  1. V has no F31 send-back.
  2. V writes no test at implement, in any slice.
  3. No harm: V's original-seed slices and deliveries pass at least as often as round 1's arm A, with as many runs.
  4. On the hollow Proof, V has no more bare dones than A.
  5. Every run finished and every send-back and hollow note is labelled.

  B's hollow count is reported as a test of the review's concern, not a rule. If 1, 2 or 4 fails, neither wording is
  merged. If 3 fails, each failing run is read, as round 1 registered.

### Amendment 2a (2026-11-01, before any run of round 2): arm V is the fourth commit

A read-only review of cb558e63 (above) found no material problem. Its one minor problem that mattered: the skill card
and the planning guide, shortened in cb558e63, applied the executed-criterion route to every criterion, which is wrong
for a searched criterion and impossible for an inspected one. Before any run of round 2, arm V moves to
132408e308a8f80ec2239cdf351c175d18e763eb, patch-id f82da38b3bf76d3512980b83f36b734431a93e29:
- the card and the guide say "for an executed criterion";
- the condition says "the step's Proof if it exercises the criterion" in place of "where";
- implement's head grows 214 characters against main, on both routes.
Everything else in amendment 2 is unchanged. "Merge the two candidate commits" in its rule means the four commits on
the branch: 97667d22, 2e2240dd, cb558e63 and 132408e3.

## Result of round 2

Not yet run.
