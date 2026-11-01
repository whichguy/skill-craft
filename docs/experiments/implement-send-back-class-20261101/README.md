# The implement send-back class, read in the 20 runs of replication R3 (2026-11-01)

Consumer: the owner, who answered "Yes, look into it" on 2026-11-01 to "Look into the implement send-back that hit 5 of 20 runs?"; and
whoever decides step-plan review §8 item 4 (F31) or reopens the proof-coverage study. Follows
[../send-back-replication-r3-20261101/README.md](../send-back-replication-r3-20261101/README.md) (the 20 runs) and the two earlier studies of the same
class: the Proof-coverage replay (`cc828f73`, [../proof-coverage-replay-20261101/](../proof-coverage-replay-20261101/)) and the step-plan review
([../step-plan-review-20261101/](../step-plan-review-20261101/), [../../shiploop-step-plan-review-2026-11-01.md](../../shiploop-step-plan-review-2026-11-01.md)
§6.1, §7a, §8). No model was run for this study: everything below is read from the saved R3 runs and from the other session's saved corpus.

## What happens

Step-plan writes, for each step, a Proof (`proof` in the step plan: the one command ShipLoop runs at implement's done, which must exit 0) and criteria whose
text ends "Confirm by: node --test runs TC_1 and TC_2": the tests the test stage writes after implement. Implement is told to "write no tests" and that "the
test stage writes them later", and its exit condition 1 says each assigned criterion is "shown by a command or file after the last edit". When the Proof is
itself the test runner on a base with no tests, it either exits 0 on zero tests (`node --test`) or exits 1 because the file it names is absent, so it
confirms nothing; implement then reports send-back, naming the criterion or command, and step-plan re-plans with a direct check (A4's packet and
contract, `implement_class.py`).

## What the 20 runs show

All of this is the shared-expenses case (a greenfield Node service whose request asks for `node --test` tests), Codex gpt-6.1-terra at high, ShipLoop 1.29.0;
`implement-class-analysis.txt` has every number.

- **Rate.** 5 of 20 runs (A 4, B 1) had an implement send-back of the class, 6 loops in all (A10 twice); 35 implement attempts in total.
- **The Proof kind separates them.** The first implement attempt of a run had a test-runner Proof in 5 runs and a direct probe (an HTTP script, `node -e`, a
  script file) in 15: **5 of 5 sent back, 0 of 15 did.** Over all 35 attempts: test-runner Proof 5 send-backs and 1 done, direct probe 28 done and 1 send-back.
  The five test-runner Proofs were `node --test` alone (A9, A10, B2), `node --test && rg ...` (A4) and a `node -e` wrapper that runs `node --test` on
  `test/service.test.js` (A1).
- **F31's wording is not the driver.** 32 of the 35 attempts had executed criteria whose Confirm by names tests the test stage writes; implement coped in 26 of
  those 32, using the Proof and its own checks. The wording is the cause of 1 of the 6 loops: A10's second, where an independent HTTP Proof passed and implement
  still objected that "C1-C3 still require unwritten TC_1-TC_4 at implement stage".
- **The shipped gate sees none of it.** The proof-order refusal (rules A, B, C of `shiploop_item_scope.proof_order_refusal`) refused 0 of the 28 accepted step
  plans on an empty base: plain `node --test` names no path (rule A needs a path, rule C needs `npm test` and a path in Confirm by), and the `node -e`
  wrapper hides its path from `command_paths`. This is the "identifier and compound forms" the closing check left unbuilt.
- **Cost.** A loop (the send-back implement plus the step-plan, test-spec and validate-existing that re-ran before the next implement) took 2.0 minutes on
  average (1.1 to 3.2, n = 6), 0.59 minutes a run over all 20 runs, on a mean of 14.8 stage minutes: 4%. Every loop recovered at the next attempt and all 20
  runs passed. The five affected runs took 16.0 minutes and 39.6M processed tokens against 14.4 and 31.5M for the other 15 (descriptive, n = 5). The Proof-coverage
  replay measured a refusal at a median 0.11 minutes (n = 100) and a proof-order send-back at a median 1.0 (n = 20).

## Candidate rules, replayed

Both are read-only replays of saved step plans (`replay_rule_s_excl.py`, `replay_rule_d.py`; outputs `rule-*-summary.txt` and `rule-*.jsonl`); "theirs" is the
other session's 171 plans with a recorded base (`../step-plan-review-20261101/traces.txt`, 112 run folders).

| Rule | My 20 runs (30 plans incl. the smoke run) | Their 171 plans |
|---|---|---|
| Rule S as the step-plan review replayed it (`replay_rule_s.py`) | 0 flagged | 12 flagged: 6 send-back, 5 done, 1 blocked |
| Rule S with `docs/shiploop` left out of the base search | 5 flagged, 5 send-back | 15 flagged: 8 send-back, 6 done, 1 blocked |
| Rule D: the first step's Proof is a generic suite command alone, and an executed criterion of that step is covered by a focused command whose IDs no base file holds | 3 flagged, 3 send-back | 11 flagged: 6 send-back, 4 done, 1 blocked |

- **A defect in the earlier replay.** From ShipLoop 1.26 on the item-base tree holds `docs/shiploop/environment.md`, which records the focused commands' test IDs, so
  `git grep` finds every ID there and rule S as written flags nothing in a greenfield run. The 12 of the step-plan review's F30 would be 15 with that folder left out;
  its conclusion (no rule precise enough) is not changed by the correction.
- **None is clean.** Pooled, rule D is 9 send-backs to 4 plans that passed (and 1 blocked), rule S with the folder left out 13 to 6. The plans that passed are, for rule D, a supplied
  checker (`gym-ui`), a deploy and `npm test` twice; rule S adds Apex test runs, inline scripts and a unittest run of a test the item itself writes. Rule D was defined here after seeing my plans (A4 and B2
  among them), so its 3 of 3 is in-sample.
- **What a gate would save here.** Rule D would have turned 3 of the 6 loops into refusals: 3 x (2.0 - 0.11) minutes over 20 runs is about 0.28 minutes a run (1.9%);
  rule S with the folder left out, 4 of 6 (the A10 second loop and A1 stay), about 0.38. Across the other session's corpus the class is 2.7% of steps, so the
  saving there is smaller still, and a refused plan that passed would cost a redraft or a stall.

## Findings and status

- **F46** (firm for this case, subject and effort): the first attempt's Proof kind separates the class, 5 of 5 against 0 of 15.
- **F47** (firm): the shipped proof-order gate refuses 0 of 28 plans; rule S as replayed was blind to ShipLoop >= 1.26 greenfield runs (above).
- **F48** (interim, n = 6 loops): a loop costs 2.0 minutes and recovers at the next attempt; 0.59 minutes a run in this case.
- **F49** (interim): F31's wording explains 1 of 6 loops; no candidate rule is precise on both corpora.

## Recommendation, and what is not known

Leave it. The class is real and common in this one case (25% of runs) and costs about 4% of a run; it recovered every time; the shipped gate cannot see it and
no candidate is clean enough to ship on the evidence of the two corpora. F31's wording change, step-plan review §8 item 4, would reach 1 of 6 loops: not worth a
packet change. If the owner wants the class gone anyway, the narrowest candidate is rule D (about 40 lines in `proof_order_refusal`, a test per branch, a
change note), with a live check that counts gate fires and any redraft that stalls; it would cut roughly half of this case's loops and risks a refusal of
`npm test` or a supplied checker that passes. Not known: how often a direct-probe Proof would have been chosen under other prompts or models; whether the 4 of 10
(arm A) against 1 of 10 (arm B) split is anything but chance (post hoc, one-sided p 0.15); the class on brownfield cases.

## Reproduce

```
python3 -I implement_class.py > implement-class-analysis.txt                       # reads ~/e2e-runs-r3/20261101 (outside git)
python3 -I replay_rule_s_excl.py TRACES.txt rule-s-excl-mine.jsonl                # TRACES.txt: the R3 runs' trace.jsonl paths, then ../step-plan-review-20261101/traces.txt
python3 -I replay_rule_d.py TRACES.txt rule-d-mine.jsonl
```
