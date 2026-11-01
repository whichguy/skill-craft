# Proof coverage and open-item stalls: a replay of the saved runs (2026-11-01)

Owner's go, 2026-11-01: "Yes, rebase and run". This answered the question "Start the saved-run replay for Proof coverage
and stalls here?". It follows the plan-time experiments study (docs/experiments/experiment-route-20261031/README.md, its
"Calibration (2026-11-01)" section) and the question-record verdicts (docs/shiploop-question-record-verdicts-and-plan-2026-10-31.md
§4, "The proof-order fault's other form").

No model runs. Everything below reads the saved runs under `~/e2e-runs*/`, read-only.

## Pre-registration (written and committed before any rule-C score or stall count)

### Q1. Does a step-plan refusal of a criterion whose Confirm by needs an unwritten test pay?

What is known before this replay:
- The shipped proof-order refusal (`shiploop_item_scope.proof_order_refusal`, ffea2956) reads only the paths a step's
  Proof names:
  - rule A: a test-class path the item base lacks, which no earlier step declares;
  - rule B: a path the base lacks, which only a later step declares.
- SG1's replay (8e5d6f47, `docs/experiments/question-record-20261031/sg1/`) labelled 12 implement send-backs. 9 were this
  fault; the shipped rule refuses 7. It misses 2 (bf-codex-r1-user-listing), whose Proofs name no test path.
- FX F s1 (2026-10-31) is a third instance:
  - The Proof is `npm test`.
  - C1 and C2 read "Confirm by: node --test test/import.test.js", a file absent at the base; the plan's own expectation E2
    says so.
  - Implement sent the plan back: "C1 and C2 require a new test file which the implementation contract forbids writing
    until test stage".
- The shipped refusal fired live in several runs on 2026-10-31.
- Rule C below has not been run on any plan.

Rule C, the candidate (implemented in this folder only):
- It applies rule A to each executed criterion a step lists in its `criteria`.
- The paths come from `command_paths`, applied to the criterion's Confirm-by command: the text after "Confirm by:" up to
  "; pass when" (or the first ";").
- It keeps rule A's exemptions: the base has the path, an earlier step declares it, or the whole item is tests.

Corpus:
- every run under `~/e2e-runs*/` that the current state reader reads;
- the same run layouts and the same base rule as `sg1/replay_d6.py`;
- each step plan the run accepted (step-plan `done`).

Labels. They are made from the implement send-back summaries alone, before rule C runs. Each implement send-back is:
- `proof-order`: the Proof, or a criterion's confirmation, needs a test or file that does not exist at that step's done;
- or `other`.

SG1's 12 labels stand. New send-backs are labelled by the same reading and listed in `labels.jsonl`, each with its quoted
reason.

Each plan rule C refuses gets one class:
- `caught`: after this plan, the item's implement sent back with a `proof-order` label.
- `hollow`: implement passed, but the step's Proof neither names the criterion's file nor runs its Confirm-by command. So
  done verified nothing for that criterion, although the duty says the Proof proves the step's criteria.
- `breach`: implement passed only because it wrote the test file, against "Write no tests". As in SG1, not counted
  against the rule.
- `false`: implement passed, and the Proof did exercise the criterion: a refusal of a plan that could run.
- `unjudged`: no base, or no implement after the plan.

Costs, from the same runs' `trace.jsonl` timestamps:
- `T_refusal`: the median minutes from a refused step-plan `check` to that action's next passing `check` or `complete`,
  over every step-plan refusal in the corpus.
- `T_sendback`: the median minutes from the first packet of an implement action that sent back with a `proof-order`
  label to the next step-plan packet for that item that the run accepted.

Decision: build rule C as a step-plan refusal (with its test and a change note) iff all three hold:
1. it catches at least 2 more plans than the shipped rule;
2. `false` is 0;
3. it saves net time: caught × (T_sendback − T_refusal) > hollow × T_refusal.

Otherwise do not build it, and record why. If (1) and (2) hold but (3) fails, the hollow count is a Proof-fidelity
finding for the owner. A refusal that costs more time than it saves, but makes Proofs prove their criteria, is a product
trade-off, so ask.

### Q2. Stalls by the open-item wording a run ran (descriptive; no decision attached)

For every traced run with a step plan, record:
- The open-item wording its step-plan packets carry (`packets/sent/*.md`):
  - `w1`: fix 1's "on an executed criterion, or on an expectation for a fact that exists" (8dee00e0);
  - `w11`: fix 11's "becomes an expectation whose `from` names it" (c2da4604);
  - `w0`: neither.
- Whether its plan left an assumption open with a due item.
- The refusals of the open-item rule in its trace, by the markers of `score_fx.py`.
- Whether it stopped at step-plan: an end state that is paused or blocked, with the last packet at step-plan.

Reported as counts per wording, with exact 95% intervals. This is observational: cases, models and hosts differ by wording.
So no cause is claimed, and nothing is adopted or rejected on it. It is the cheap stand-in for the controlled measurement
of fix 1's benefit, which would need about 25 runs a side.

Outputs in this folder: `replay.py`, `labels.jsonl`, `plans.jsonl`, `stalls.jsonl`, `scores.json`. Results are appended
below after the run.

### Amendment, 2026-11-01, before any score (found while building the reader)

Building the reader exposed a flaw in Q1's classes, not in its data. A criterion's Confirm by often names the focused test
the test stage writes, while the step's Proof proves the criterion another way: a probe script, or an existing test. FX F
s1's revised plan is one such case, `node ../run/scratch/import-probe.js && npm test`. Under the registered `hollow`, a
Proof like that "names neither the criterion's file nor its Confirm-by command", so it would count as hollow. It is not:
the probe exercises the criterion. That would inflate `hollow`, and with it decision item 3.

So, before anything is scored:
- **Rule C′ is the primary candidate.** It is rule C restricted to steps whose Proof names no repository path at all
  (`command_paths(proof)` is empty, as with `npm test` or `pytest`). This is the exact "other form" that verdicts §4
  names, and all three known instances have it.
- **For C′, `hollow`** means implement passed with that generic Proof, so the step's done ran nothing specific to the
  criterion.
- **`caught`, `breach`, `unjudged`, the costs and the three decision items are unchanged**, applied to C′.
- **`false` is near-empty by construction.** A Proof that names no path cannot exercise an unwritten test unless implement
  wrote it, and that is `breach`. Decision item 2 therefore checks the reader: for example, a Confirm by misread, or a
  "test" path that classify misplaces. It cannot check the rule.
- **Rule C, unrestricted, is reported beside C′ as descriptive only.** No decision rests on it.


## Results (scored 2026-11-01 06:14 PST)

The corpus at that time:
- 1,863 accepted step plans in 246 run folders under 14 roots;
- 365 of them judged, meaning the run's repository still has the base.

Other sessions were adding runs while this ran, so a rerun reads a few more.

`labels.jsonl` holds 35 implement send-backs:
- 20 are labelled `proof-order`. SG1's 12 reproduce 8e5d6f47's judgement: 9 proof-order, 3 other.
- 3 of the others carry the sub-label `shell-quoting`.

### Q1: no new proof-order rule

The shipped rule (A, B) refuses 14 judged plans, and comes before 11 of the 20 proof-order send-backs.

| Rule | Plans refused | Caught | Caught beyond shipped | False | Hollow | Unjudged |
|---|---|---|---|---|---|---|
| C′, registered (the Proof names no repository path) | 10 | 3 | 3 | 5 | 1 | 1 |
| C, descriptive (every Proof) | 12 | 4 | 3 | 6 | 1 | 1 |
| C on generic suite Proofs only, post-hoc | 3 | 2 | 2 | 0 | 1 | 0 |

Costs:
- `T_refusal`: median 0.11 minutes, n = 100.
- `T_sendback`: median 1.0 minute, n = 20. The range is 0.6 to 5.7, and the total 24.5.
- An Improve review of the re-planned step plan, where one followed and could be timed (5): median 1.0 minute, at
  most 7.4. Not registered; reported only.

Decision, by the registered rule on C′:
1. It catches 3 plans beyond the shipped rule. Met.
2. False is 5. **Not met.**
3. Net saving is +2.5 minutes.

**C′ is not built.**

Why item 2 fails: the reader. `command_paths` skips absolute paths, `../` paths and inline code. So "the Proof names no
repository path" also covers Proofs that test the step directly, and implement passed all five with one:
- `node /Users/dadleet/e2e-runs/20261025/gate-2132-…` (the gate-2132 battleship, two plans), a scratch proof script;
- `node --test ../run/scratch/proofs/W1-S1.test.js` (bf-ds-ticket-escalation);
- `node -e "…filterUsers…"` (bf-ds-user-listing);
- `node -e "eval(Buffer.from('…'))"` (B-ticket-assignment-s2).

The amendment expected `false` to be near-empty. It was wrong about the reader.

Post-hoc, not adopted: rule C restricted to generic suite Proofs (`npm test`, `pytest`, `python3 -m unittest -v`;
`generic_proof` in replay.py).
- It meets all three items here: 2 caught (bf-codex-r1-user-listing's first plan, FX F s1), 1 hollow
  (A-ticket-assignment-s1), 0 false, net +1.65 minutes.
- But it was defined after seeing these plans and rests on 2 catches. Adopting it would need runs it has not seen.

What the shipped rule misses, 9 of 20:
- 3 that the candidates see: a criterion's Confirm by names an unwritten test file.
- 6 that name the test by identifier or in prose, which no path reader sees:
  - `test_hello.GreetingTest.test_TC_1` (live/run);
  - "unittest" (hook-missing-done W2);
  - an Apex test class (battleship-candidate; SLGymControllerTest in the gym);
  - `python3 -m unittest -v`, with no tests yet (csv-published-discovery-01);
  - "Confirm by: focused and full tests" (B-ticket-import-s4).

The stakes are small:
- A proof-order send-back costs about one minute of wall time (median, n = 20), plus about a minute of Improve review
  where one follows.
- Implement stops early: in 19 of the 20, the send-back and the re-plan together take under 2 minutes.
- All 9 misses come to about 10 minutes across 365 judged plans.
- ffea2956's message says each is "found only after a whole implement Until Loop and an Improve review". In wall time,
  that overstates it.

So no proof-order rule is added. Reopen this if a proof-order send-back costs a run more than a few minutes, or a host or
model makes the fault frequent.

### Q2: no stall under fix 1's wording; observational

| Wording | Runs | With an open item due | Stopped at step-plan | Stop rate, exact 95% | Runs with open-item refusals |
|---|---|---|---|---|---|
| w0, before fix 11 | 125 | 33 | 4 | 12% (3.4–28.2%) | 34 |
| w11, fix 11 (2.26.2) | 11 | 6 | 0 | 0% (0–45.9%) | 3 |
| w1, fix 1 (2.27.0 on) | 38 | 14 | 0 | 0% (0–23.2%) | 4 |

- Every stop had an open item due. The four are all on Codex Terra 6.1: XI A s1, s4 and s6 (ticket-import), and
  hooks-before-ticket-escalation-attempt1 (2026-10-29). So the stall was not peculiar to XI's case.
- Against w0, one-sided Fisher gives p 0.23 for w1 alone, and p 0.14 for w11 and w1 together.
- This is consistent with fix 11 and fix 1 removing the stall, but it is not evidence of it: cases, models and hosts
  differ by wording.

Reader check:
- The first marker for fix 11 also matched the wording that c2da4604 replaced, so XI arm A read w11. Arm A ran 02a215e9,
  which lacks c2da4604.
- Packets are hard-wrapped, which hid fix 1's sentence from the first reader.
- The reader now matches each full sentence on whitespace-collapsed text. Checked: XI A s1–s6 and B s1–s5 and s7 read w0;
  FX P s1–s4 read w11; FX F s1–s4 read w1.

## Follow-up: the narrow check, built for the Proof duty (pre-registered 2026-11-01, before the held-out score)

Owner, 2026-11-01: "Do we need to do the second proof check? Propose and implement a plan".

Proposal:
- Not for time: Q1 puts every miss together at about 10 minutes in 365 plans.
- For rigour. The step-plan duty says a step's `proof` is "the one command … that proves the step's criteria … ShipLoop
  runs it at the step's done".
- A plain suite command cannot do that for a criterion whose confirming test is not written yet. In
  A-ticket-assignment-s1, implement passed with `npm test` while C1's Confirm by named the unwritten
  `test/assignment.test.js`, so its done proved nothing about C1.
- Q1's post-hoc variant is exactly that case. In-sample it refused 3 plans: 2 caught, 1 hollow, 0 false.

Frozen rule, rule C of `shiploop_item_scope.proof_order_refusal`:
- For each step whose Proof is a generic suite command (`generic_command`: no script or test path in any form, absolute,
  `../` or relative, and no inline code).
- For each executed criterion that step lists: refuse when the criterion's Confirm by (`confirm_by_command`: the text after
  "Confirm by:" up to "; pass when" or the first ";") names a test-class path that the item base lacks and no earlier
  step declares.
- The whole item being tests exempts it, as for rule A.
- The reading is replay.py's `generic_proof` and `confirm_by`, moved unchanged.

Held-out set: run folders whose `state.md` was created after this replay's snapshot (2026-11-01 06:14 PST). There are 42
when this is written.

Ship iff all three hold:
1. **The move kept the reading.** On every judged plan of the full corpus that rules A and B pass, the shipped function
   refuses exactly the plans that replay.py's `rule_c_generic` refuses.
2. **No false refusal on held-out runs.** Every held-out plan it refuses is genuine on reading: the step's Proof is a
   generic suite command, and the cited criterion's confirming test is absent at the base. A reader error counts as
   false, and false must be 0. Held-out catches are not required: at about 1 plan in 120, 42 runs are unlikely to hold
   one.
3. **The tests pass.** Its route test passes (refused, then the corrected plan accepted through the real gate), and so
   does the quick tier.

### Follow-up result (2026-11-01): shipped

1. **The move kept the reading.** `replay.py shipped` writes `shipped-check.json`. On all 374 judged plans that rules A
   and B pass, the shipped function refuses exactly the plans that replay.py's `rule_c_generic` refuses: 0 mismatches.
   In-sample, these are the 3 plans of Q1's post-hoc row.
2. **No false refusal on held-out runs.** 42 runs were created after the snapshot, and rule C refuses none of their
   plans. That is 0 false, and also 0 caught, as expected at about 1 plan in 120.
3. **The tests pass.** All of these pass, and all fail on the old code (2 failures and 1 error):
   - the route test: refused, then the same callback accepts a direct Proof, and a plain suite Proof is accepted when the
     base has the test;
   - the reader test, for `generic_command` and `confirm_by_command`;
   - the Checked-by guard row.

   The quick tier result is in the commit.

Decision: shipped in ShipLoop as a patch (`changes/shiploop/proof-order-plain-suite-proof.md`).
- The packet text is unchanged. Step-plan's Checked-by line already names "a Proof needing an unwritten test".
- The commit carries a No-E2E-Round reason. Rule C fires in about 1 plan in 120, so a live round would not exercise it.

## Closing check (registered 2026-11-01, before it ran)

Owner, 2026-11-01: "Determine how to conclude, plan out, and implement."

The study closes on this check. Rule C shipped with two open limits (journal E18). Its in-sample case is 3 plans chosen
after they were seen, and the 42 held-out runs held no catch. Other sessions have made many runs since: 1,194 run folders
have a `state.md` created after the snapshot, 981 of them after the release (26123c9e, 07:13 PST).

Done before this was written (a count; no rule scored):
- No run record under `~/e2e-runs*/` holds rule C's refusal text, "runs only the tests the item base has".
- Its 21 hits are copies of `test/shiploop-callback-contract.test.py` inside run trees, and one code review's transcripts.
- A run's trace does keep a refused check's message, in the row's `error`. The focused-ID gate's refusal is in the trace
  of sp1-xhigh ticket-import-s3.

Method: `replay.py closing SCRIPTS ~/e2e-runs*`, on every run whose `state.md` was created after the snapshot. Each run is
one of three kinds:
- **live**: its ShipLoop had rule C. Either its checkout's `local_head` (in `invocation.json`) descends from 9870c6f6,
  or its `shiploop_version` is 1.26.4 or later. A rule-C refusal in its trace is a live fire.
- **replayed**: an older ShipLoop.
- **unknown**: neither is recorded.

The shipped rule runs on every kind's accepted step plans, after rules A and B pass, as in `shipped`. On a live run an
accepted plan has already passed the gate. A replayed refusal there would mean the gate did not run on that plan's route,
and that is reported as a defect.

Each live fire and each replayed refusal is read and classed by ship check 2's definition. It is genuine when the step's
Proof is a generic suite command and the cited criterion's confirming test is absent at the base. A reader error counts
as false.

Decision rule:
- **Any false one, or a live-run refusal:** fix rule C or the gate in a patch, with the case as a test, before the study
  closes.
- **None:** rule C stands, and the study closes. Its rate is stated as an exact interval over all judged plans. If the
  in-sample rate held (about 1 plan in 120), the live plans would hold about one fire per 120. The result states the
  chance of seeing none at that rate.

### Closing check result (2026-11-01): rule C stands, and the study is closed

`replay.py closing` writes `closing-check.json`. The numbers below are from its second pass, at 10:50 PST.
- **Live fires: 0.** 289 new runs had rule C, and their 82 judged step plans passed it with no refusal in any trace. The
  file grep of the registration agrees.
- **Replayed refusals: 0.** 277 new runs had an older ShipLoop. The shipped rule refuses none of their 65 judged plans.
  No accepted plan of a live run is refused either, so no route skipped the gate.
- **Plans: 147 judged, in 112 runs.** One more plan had no recorded base. At the in-sample rate (3 in 374), 147 plans
  would hold about 1.2 refusals, and none happens 31% of the time (82 live plans: 0.66 expected, none 52%). The exact
  95% interval for 0 of 147 is 0 to 2.5%.

Reader audit, done before the decision:
- The first pass (`closing-check-pass1.json`) counted 1,374 run folders, most of them copies of saved runs inside
  checked-out skill-craft trees: test fixtures, a docs fixture, worktrees and marketplace copies. A count between the two
  passes found 846 copies among 1,413 folders. A copy's `state.md` is new, but the run it copies is not.
- The copies' 400 accepted plans record no repo, so none was judged, and the first pass's 0 fires and 0 refusals stand.
  Its 136 judged plans all came from runs of their own.
- The second pass sets copies apart (`inside_checkout`: a folder above the run holds `skills/shiploop/SKILL.md`) and
  counts plans with no repo as having no base. It found 850 copies and 0 runs of unknown version, and adds the runs made
  in between.

Decision: rule C stands, as registered. No live fire or refusal was read false. Neither pass had a fire or refusal to
read, so this check rules out false refusals; it says nothing new about how many real cases rule C catches.

Remaining, not built:
- A test named by identifier (a unittest name, an Apex class) or a compound Proof. E17 counted 6 such misses at about a
  minute each, and the step-plan review (journal E19, F30) found no generic rule precise enough to gate on.
- Implement's side of the same gap, journal F31. Implement reads a criterion's Confirm-by test as due at implement,
  although the test stage writes it later. This is the owner's decision (`docs/shiploop-step-plan-review-2026-11-01.md` §8,
  item 4).

Reopen this study if any of these happens:
- a live rule-C refusal is read as false;
- a send-back of the identifier or compound form costs minutes rather than about one;
- the owner takes up F31.
