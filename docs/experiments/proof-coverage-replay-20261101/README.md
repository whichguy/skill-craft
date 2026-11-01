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
