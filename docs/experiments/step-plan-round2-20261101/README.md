# Step-plan round 2: the open items, re-run and built (2026-11-01)

Consumer: the owner, who asked (2026-11-01) "I want to plan out all of these, rerun as needed, and re-implement or implement new
tests. Pursue F31-side experiment on Terra XAI if needed", about the open items of the step-plan review
([docs/shiploop-step-plan-review-2026-11-01.md](../../shiploop-step-plan-review-2026-11-01.md) §6 and §8); and the session that
reads the results below to keep or revert each change. Journal: docs/shiploop-question-driven-planning-journal.md, E22.

This file is written and committed **before** any scored sample. The rules are not edited; results are appended under "Results".

## The owner's decision, before any sample (2026-11-01)

Two other sessions held parts of this round's plan when it started:

- The implement send-back study (27c453fa, recorded in a032bb16) recorded the owner's "Yes, leave it" at 13:48: the class stays as it is, proof-order
  rules A to C stay as they are, and rule D is not built.
- The F31 session registered F31's own live check (c2b85410) with the same wording fix (97667d22). The owner told it to "Run the live check"
  (f5fb7d64).

Asked which should stand, the owner chose **"Reopen the class, leave F31"**. The option text: "Run my step-plan replay experiment (X-A) and build A1 and A2
only if they meet their pre-registered rules. That reverses your 13:48 'leave it' for this class, backed by new evidence. F31 stays with its own
session; C1 is dropped here."

So this round runs X-A, A1's replay and D. It does not run C1 or an F31 experiment; the F31 implement scenario built for it was removed before
any sample. Rule D stays unbuilt. Both sessions were messaged with the owner's words.

The study's numbers are the class's measured base and cost here: 20 R3 runs of shared-expenses at Codex Terra high.

- An implement send-back came in 5 of the 20 runs, 6 loops in all.
- A loop cost 2.0 minutes on average (1.1 to 3.2), about 4% of a 14.8-minute run, and every loop recovered.
- The first attempt's Proof kind predicts the send-back: a test-runner Proof sent back 5 of 5 times, a direct probe 0 of 15.
- F31's wording caused 1 of the 6 loops.

## What is being fixed, and why now

- **The Proof that runs this item's unwritten tests** is still the largest live send-back class. On today's `main`, in R3, another session's round
  on the new `shared-expenses` case at Codex Terra high, it sent back 3 of the first 6 finished runs. Those runs are
  `~/e2e-runs-r3/20261101/smoke-b-s1`, `A-shared-expenses-s1` and `A-shared-expenses-s9`; they are read only, and their numbers are
  provisional until R3's results commit. The study of all 20 R3 runs, cited above, has 5 of 20. Neither form below is refused by rule A or rule C
  (`shiploop_item_scope.proof_order_refusal`):
  - **Form 1, a path inside inline code.** A-s1's S1 Proof is `node -e '…execFileSync(process.execPath,["--test",…,"test/service.test.js"])…'`.
    `command_paths` skips inline code.
  - **Form 2, the focused suite itself.** A-s9's Proof is `node --test`, and the smoke run's is `node --test && rg …`. SP1 xhigh csv-report s1's is
    `python3 -m unittest -v && rg …`. Their criteria name IDs, not a path, so rule C does not fire.
  - A-s9's knowledge home records "node --test is the requested verification" under `## Commands`. Step-plan duty 4 says the Proof
    needs no unwritten test "(reuse a recorded command that proves them)" (12151c49).
  - E21 closed the proof-coverage study with exactly these forms "not built" and said to reopen it when they cost minutes or when the owner takes up
    F31.
- **F31** (implement reads a criterion's "Confirm by" test as due at implement) is not changed here. It is the F31 session's live check
  (c2b85410), by the owner's answer above.
- **Test-spec RED.** test-loop.md's base run accepts a new test that fails "to load the code this item adds". Test-spec duty 3 does not
  say so, and SP1's pilot csv-report s2 test-spec sent a plan back for exactly that: "an interpreter file-not-found failure does not
  establish a missing behavior".

- **Corpus refresh** (`corpus/`, read-only, before any sample). The review's tool (`../step-plan-review-20261101/step_plan_review.py`) was rerun on
  229 runs with more than 30 trace events: the review's 112 plus every run made since. The result is 338 step-plan actions and 91 send-backs
  to step-plan. The send-backs on ShipLoop 1.27.0 and later (30), read from their headlines and summaries (`corpus/sendback_classes_127plus.jsonl`):
  - 12 are a Proof that runs this item's unwritten tests, 11 as the main class and 1 beside another. They take a path, identifier
    (`test_hello.C1`) or plain-suite form.
  - 11 are a focused command short of IDs, all on 1.27.0, which the 1.28.0 gate now refuses.
  - 4 are test-spec refusing RED on an empty base, 2 as the main class and 2 beside missing IDs. Example: "the empty base has no executable, so the
    required behavioral RED cannot be observed without treating a missing file as failure".
  - 3 are a runner or command kind, 1 is F31, 1 needs a later step, and 1 is a wrong expectation.
  - The RED class is D's target. It is wider than the one pilot case the review had, and the test-spec template's own RED placeholder reads
    "fails on the item's base because the behaviour is missing, not because a file is" (145aefbb), against the base run, which accepts a test
    that fails "to load the code this item adds" (`shiploop_test_loop.BASE_RULE`). D changes that placeholder too.

## Changes under test (arm T; each its own commit on branch `stepplan2-cf7d87`)

- **A1** (gate). Rule A also reads the test-class paths inside a Proof's inline code (the word after `-e`, `-c`, `--eval`, `-p`). Its exemptions and
  message are kept.
- **A2** (step-plan duty 4, the `proof` bullet), in three parts:
  - The parenthetical becomes: never the focused command, whose tests the test stage writes after implement.
  - ShipLoop reruns the Proof at the step's done, so it must be safe to repeat. That is the check bullet's term; the decided invariant is that a
    rerun gives the same result and leaves the same state.
  - The planning review focus's steps condition also names "an unwritten test".
- **D** (test-spec duty 3, the template's `red` placeholder, the glossary's RED). A case's RED may be that the code this item adds is not there
  to load; a guard that only checks a file is still not RED. This is the base run's own rule, worded where test-spec reads it.

Arm B = `main` at **49d21bc5bd3c76dfd5a3a9b1c88a840c022bb019**, the branch's base. Arm T = the branch commit that holds the three changes; its hash is
recorded under "Results" before T's first sample.

## Apparatus

The stage suite's live tier (`test/shiploop_e2e/stage_suite/`): `stages.py live <scenario> --ref <arm commit>`.

- It builds the plugin from that commit, and seeds a run to the scenario's stage through the engine's own seam with the recorded results.
- A model follows that one packet. The sample stops when the seeded action is accepted with any outcome, or parks at its Improve stage, so the
  Improve review is not measured. The oracle grades the result.
- The scenarios and harness are this branch's; only the plugin differs between the arms.
- Runner, every sample: Codex `gpt-6.1-terra` at `xhigh` (`--host codex --model gpt-6.1-terra --effort xhigh`), the owner's runner. Each sample's
  `invocation.json` records the requested model and effort; the served identity is not observable beyond Codex's own session log.
- Runs: `~/e2e-runs-sp/20261101/round2/<experiment>-<arm>[N]/`, outside git.
- Scores: `score_xa.py` writes `xa_scores.jsonl` here.

The scenario replays a real state, so the trigger is in front of the model in every sample. F17 (E8) found a step case's own seed
carried a clean `node -e` Proof; this seed carries the live run's knowledge home and records instead:

- **X-A, `step-plan/proof-runs-focused-suite`.** A-s9 at step-plan:
  - the fixture `shared-expenses-at-step-plan` (its knowledge home at 9af95f74);
  - the step case `shared-expenses-w1` (its prompt and work item);
  - its test-strategy rows and the open assumption A2 due at W1.
It passes the suite's verify and render tiers (no model).

## Scorers (validated before any scored sample)

- **`proofscore.classify`** (X-A's measure) decides, per step, whether its Proof needs a test not yet written.
  - **Form 1:** a test-class path in the Proof's words or inline code that the base lacks and no earlier step declares.
  - **Form 2:** a whole shell segment equal to a focused command that names no path and no inline code, while no code or test file of the base holds its IDs.
  - An item that is all tests is exempt. The knowledge home is not searched for IDs, because A-s9's environment.md lists the planned TC_1-TC_5.
- **`test_scorers.py`** (10 tests, all pass):
  - Real plans: A-s1 is form 1 on S1 only; A-s9, the smoke run and csv-report s1's first plan are form 2. The smoke run's and csv-report's
    replanned plans are clean.
  - Exemptions: a later step running an earlier step's test, a direct assertion, an all-tests item, a base test holding the IDs, an absolute
    scratch path in inline code.
  - Run: `python3 -I docs/experiments/step-plan-round2-20261101/test_scorers.py`.

## Rules (decided now)

### X-A (step-plan; A1 and A2)

- **Pilot.** Arm B, 4 samples. The study's rate is a test-runner first Proof in 5 of 20 runs, so the arms are sized for a rate near 25%.
  - If B has a faulty plan (form 1 or 2) in at least 1 of 4: run 12 per arm. The pilot is B's first 4.
  - If B has none in 4: run 4 more B. If B has none in 8, the replay does not reproduce in isolation. Then fall back to whole deliveries,
    `run.py --case shared-expenses`, 6 per arm, with the same measure on each run's first accepted step plan.
- **A2's rule counts form 2 only.**
  - A2 ships if T has form 2 in at most 1 of its samples and B's excess over T is significant: exact one-sided Fisher p at most 0.10.
    At 12 per arm that needs, for example, B at least 4 with T 0, or B at least 6 with T 1. At a true 25% against 0%, B reaches 4 of 12
    about 35% of the time, so "not shipped" at this size is weak evidence against A2.
  - Form 1 belongs to A1. A1 is judged by its replay below. In arm T it shows as `check` refusals in the sample's trace, and no accepted T plan
    should hold form 1.
- **Controls.** T's control failures are at most B's plus 1. A control failure is any of:
  - an outcome other than done;
  - an executed criterion without its own focused ID (`criteria_without_ids`);
  - no focused command.
- Secondary measures, reported and not ruled: step-plan refusals, sample minutes.

### A1's replay

Rule A with inline code is replayed over every saved accepted step plan that has a recorded item base. That is the step-plan review's corpus
(`../step-plan-review-20261101/traces.txt`) plus the runs of 2026-11-01. Each flagged Proof is listed with its step's implement outcome.

- A1 ships if it flags no Proof that passed its implement unchanged.
- A flag on a Proof that passed is read, and A1 is either narrowed (re-replayed) or dropped.

### Needs-later-step replay

(Result: `replay_rule_b_minimum.py` on the same 843 traces, 363 plans with a base: 0 flags. #32's later file is imported, not named, and
#49 is a case assigned to the wrong step, so no path rule reaches either. Not built.)


A rule B extension is replayed on the same corpus. It covers paths named by the `minimum` regression command that the base lacks and only a later
step declares. It ships only if it flags #32 or #49 of the corpus and nothing that passed. The expectation is that it is not built: #32's later
file is imported, not named.

### Eligibility and missing samples

- A sample counts if its host reached acceptance of the seeded action.
- A harness or host failure before that is rerun once, and both attempts are kept. Such failures are a crash, a timeout, a credit or network
  failure, or `error.txt`.
- A second failure is listed as missing. The rule's arithmetic is then also printed with each missing sample counted for each arm.
- Every attempted sample stays under the runs root.

### Attribution

A1, A2 and D are separate commits. A component that misses its rule is reverted from the branch before merge. The hermetic suites and
head tables are then rerun, and the release round runs on what remains.

## Release round (whole deliveries; ShipLoop's E2E round before release)

- **What runs:**
  - the branch with whatever survived, from its own checkout, `test/shiploop_e2e/run.py`, Codex Terra 6.1 xhigh;
  - `shared-expenses` ×3 and `csv-report` ×3: empty bases that reach A1, A2 and D, and no port lease.
- **Predictions:**
  - no implement send-back because a Proof runs this item's unwritten tests (a confirm-by send-back is F31's, counted and not ruled here);
  - no test-spec send-back for RED;
  - every hidden check passes.
- **Responses:**
  - A send-back of the targeted family (unwritten tests, RED) means that change does not work: stop, find why, and do not release it.
  - A hidden-check failure is compared with the case's rows on `main` (SP1, R3). If it is not explained, there is no release.
  - A send-back of another class is recorded and does not block.

## Release round, as it runs (registered before its first delivery, after X-A's verdict)

A2b was reverted (68985caf). The branch, with origin/main merged in at 2b97a07e (ShipLoop 1.30.2 plus A1, A2a and D), runs the release round
from its own checkout. The launcher is `launch_release_round.sh`, with lanes of 3, run.py, Codex Terra 6.1 xhigh and `--source checkout`.
It runs `shared-expenses` s1 to s3 and `csv-report` s1 to s3 into `~/e2e-runs-sp/20261101/round2-release/`.

- **Predictions:**
  - no implement send-back of form 1, a Proof whose inline code runs a test file the base lacks, because A1 refuses that at step-plan;
  - no test-spec send-back for RED on the empty base (D);
  - every hidden check passes: shared-expenses 6 of 6 and csv-report 5 of 5 per run.
- **Counted, not ruled:**
  - form 2 send-backs (the focused suite verbatim or filtered), whose wording change did not ship;
  - F31 confirm-by send-backs, which belong to the F31 session's check;
  - every other send-back.
- **Responses:**
  - a form-1 or RED send-back means A1 or D does not work: stop, find why, and do not release that change;
  - a hidden-check failure is compared with the cases' rows on main (SP1 xhigh csv-report 3 of 3 pass; R3 shared-expenses 20 of 20 at
    high). If it is not explained, there is no release.
- **The scorer** is `score_release.py`. It reads each run's `result.json`, its hidden checks, and every send-back with its stage and
  summary. Classes come from the same reading as `corpus/sendback_classes_127plus.jsonl`.

## Not ruled here

- **Proof command defects** (quoting, a wrong API, a wrong state transition) get no build. `bash -n` catches none of them, and a dry run can
  deploy. Their count is refreshed.
- **§8.2, the step-plan Improve review per item.** It is a product-behaviour trade-off held for F1's three-arm measurement. That measurement
  belongs to another session, which gets the step-plan numbers.

## Reproduce

```
python3 -I docs/experiments/step-plan-round2-20261101/test_scorers.py
python3 test/shiploop_e2e/stage_suite/stages.py live step-plan/proof-runs-focused-suite --host codex --model gpt-6.1-terra \
  --effort xhigh --ref <arm commit> --samples 4 --jobs 2 --out ~/e2e-runs-sp/20261101/round2/xa-<arm>
python3 -I docs/experiments/step-plan-round2-20261101/score_xa.py B=<root> [B=<root2>] T=<root> --out xa_scores.jsonl
```

## Amendment, before any arm T sample (2026-11-01, after arm B's pilot)

Arm B's 4 pilot samples (on 49d21bc5, Codex Terra 6.1 xhigh, about 70 seconds each) produced a third form that the registered scorer does
not count.

- **The third form.** Sample 4 proves S1 with `node --test --test-name-pattern='TC_2|TC_5' && rg 'HTTP contract' server.js`, S2 with
  `node --test --test-name-pattern='TC_1|TC_3'` and S3 with `node --test --test-name-pattern=TC_4`. Each is a filtered copy of its focused
  suite (`node --test --test-name-pattern='TC_1|TC_2|TC_3|TC_4|TC_5'`), with no file.
  - On the empty base node's runner finds only this item's test files, and each step's own cases are written after that step's implement.
    So every one of these Proofs runs no test at its step's done. That is the class's fault.
  - Form 2 as registered needs the focused command verbatim, so it misses this.
  - Samples 1 to 3 are clean under either reading. Two of them run node's runner on a scratch file the step plan wrote, which exists at the
    step's done; the third runs that scratch file with `node`.
- **The amended measure.**
  - Form 2 now counts `form2_filtered` as well (`proofscore.classify`). This is a whole segment that names no path or inline code and runs
    the same program (its first two words) as a generic focused command whose IDs no base code or test file holds.
  - The registered verbatim reading is reported beside it in every table (`faulty_registered`).
  - `test_scorers.py` gains the pilot's samples 1 and 4 and a filtered suite whose IDs a base test holds (13 tests, all pass).
- **What follows from the amendment.**
  - The pilot reads 1 of 4 under the amended measure (sample 4) and 0 of 4 under the registered one.
  - The amended branch is taken: 12 per arm. B's pilot is its first 4, so 8 more B samples run.
  - The registered branch would have run 4 more B samples, so B gets those either way.
- **A2's rule, amended.** T has form 2 (verbatim or filtered) in at most 1 of 12, and B's excess over T is significant: exact one-sided
  Fisher p at most 0.10. The verdict under the registered reading is reported too. This amendment is made after seeing arm B's data and
  before any arm T sample; it widens what counts as the fault, not what counts as a success.

## Results

| Run | Arm | Samples | Faulty (amended) | Form 1 | Form 2 verbatim | Form 2 filtered only | Faulty (registered) | Short of IDs | Not done | Refusals |
|---|---|---|---|---|---|---|---|---|---|---|
| pilot | B (49d21bc5) | 4 | 1 (sample 4) | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| rest | B (49d21bc5) | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **B total** | B | **12** | **1** | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| **T total** | T (c7679685) | **12** | **0** | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Arm B, read before any T sample:
- **The fault in the replay.** 1 of 12. The other 11 plans prove each step with a scratch script the step plan wrote in RUN/scratch,
  which exists at the step's done. Eight of them run it with `node`, and three run it through node's runner with a name filter.
- **Comparison with R3.** R3 had 5 of 20 at Terra high in whole deliveries. At xhigh, in this replay of A-s9's state, the fault is rare.
- **Consequence for A2b.** With B at 1 of 12, even T at 0 of 12 gives one-sided Fisher p = 0.50. A2b's rule cannot be met at this size and
  this rate, so the rule's verdict on A2b will be "not shipped" whatever T shows.
- **Why T still runs.** T's 12 samples run as registered, for the controls: outcome done, an ID for each executed criterion, a focused
  command kept. They also show whether arm T's gate (A1) or wording (A2a, A2b) adds refusals or new faults.
- **Arm T** = **c767968528e3db301da38bd4e821f923ac440563** (branch `stepplan2-cf7d87`: A1 b8ad4478, D e47c8d32, A2a 211fe61b, A2b c7679685).

**X-A verdict (registered rule, amended measure).**
- **Counts.** T 0 of 12, B 1 of 12. The exact one-sided Fisher p for B above T is 0.50. Under the registered reading it is 0 of 12 each.
- **Controls.** No sample in either arm ends other than done, leaves an executed criterion without its ID, or drops the focused command. T's
  control failures (0) are within B's (0) plus 1.
- **Cost.** Step-plan host time: median 1.04 minutes in B, 1.10 in T. No refusal in either arm, so A1's gate never fired: no plan wrote the
  inline-wrapper form.
- **A2b does not meet its rule.** T is at most 1 of 12, but B's excess is not significant: p = 0.50 against the registered 0.10. A2b is
  therefore reverted from the branch before merge, as registered. Its change is the proof bullet's "so never the focused command or a
  filtered copy of it" and the review focus's "or an unwritten test".
- **What the verdict means.** On the owner's runner the replay rarely shows the fault, so there was nothing for A2b to remove. That says the
  fault is rare in this state at xhigh. It does not say A2b is useless or harmful: R3's whole deliveries at Terra high had 5 of 20.
- **What ships from X-A's side.** A1 rests on its own replay (0 false flags in 363 plans) and adds no refusal here. A2a (safe to repeat) and D
  (RED) were never ruled by X-A, and they ship to the release round.

Evidence: `xa_scores.jsonl` (score_xa.py); the runs in `~/e2e-runs-sp/20261101/round2/xa-B/` `xa-B2/` and `xa-T/` (outside git).
