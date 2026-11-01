# Plan-time experiments in ShipLoop planning (2026-10-31)

The owner, 2026-10-31: "I was noticing that sometimes planning out and implementing experiments, or adding extended
tests on existing code base can clarify conditions, state & system behavior. Not sure if we would introduce that into a
prompt or a specific step enforced by scripts", then "Do all" to this plan: a no-tool routing test, a required experiment
route built as a candidate, existing-code cases where reading misleads, and a live A/B on the Codex harness (Terra 6.1
high, all tools, 6 runs per side).

Prior evidence: plan-time experiments are offered and unused (docs/shiploop-planning-pipeline-2026-10-30.md F7: no live
run records a `probed` assumption; the 2026-09-21 pilot found no consequential gain); in the four live runs of
2026-10-31 that stored an intake ledger, 1 of 10 questions took the `experiment` route
(../question-record-20261031/scores-e2e-ab.json and the runs under ~/e2e-runs-qr/20261031).

## E12. Corpus: do runs miss runtime facts or break existing behaviour? (run first; objective, not pre-registered)

Every saved product of the node-tickets cases, copied and started outside the run (corpus/):

| Probe | What it asks | Result |
|---|---|---|
| `probe.mjs` on the base | 36 claims of docs/api.md and docs/operations.md against the running base | 35 hold; 1 drift: filters OR (`matchesFilters` uses `some`) where the docs say they combine |
| `combine.mjs` | do the product's filters combine (status+priority, assignee+status)? | AND in 17 of 18 completed products; OR in 1 (bf-ds-r1, DeepSeek flash, which never implemented assignment) |
| `restart.mjs` | does a ticket keep its assignee across a SIGTERM restart (DATA_FILE)? | 17 of 17 products that implement assignment |
| `escalate.mjs` | escalated at most once across a SIGTERM and a SIGKILL restart? | 5 of 5 completed escalation products; 2 interrupted runs never built it |
| `probe.mjs` on each product, diffed with the base | any documented claim broken, or any of 7 undocumented behaviours changed? | 0 of 17 products |

And the harness's own held-out acceptance (result.json `quality.acceptance`) over every saved brownfield run: 26 of 26
completed runs pass every check (ticket-assignment 10 runs x 18 checks, ticket-escalation 5 x 14, user-listing 11 x 11),
DeepSeek flash and Codex Terra, both arms of the 2026-10-31 A/B. Those checks include the latent facts the cases were
built to hide (filters that combine, a dropped partial last page, old data files, state across restarts, escalation at
most once).

Reading: on the cases we have, runs already find the system's runtime facts and keep its behaviour. A required
experiment step or characterization tests would bind nothing there; the live A/B needs a case whose deciding fact only
running settles.

## XR. Does one sentence move runtime questions to the `experiment` route? (pre-registered)

- Subject: Codex `gpt-6.1-terra` at high (run.py: throwaway CODEX_HOME, read-only, ephemeral, no tools in the frame).
- Prompts (build_routing.py): X1's intake exercise frame, unchanged, with ShipLoop's shipped intake duty (main 02a215e9).
  Arm A: as shipped. Arm B: the `experiment` route reads "experiment: only running something answers it, as for how fast
  or how much the existing system handles, what it keeps across a restart or a concurrent change, and what it really
  does where its code, documents and tests disagree;". Nothing else differs.
- Requests: the live prompts of user-listing, ticket-assignment, ticket-escalation, and ticket-import (XI). 4 samples per
  case and arm: 32 calls.
- Judge (Opus, one call per case and sample pair; arms shuffled and relabelled; the judge sees each question's id,
  category, text and `changes`, never its route): each question is RUNTIME when settling it reliably needs the existing
  system observed while it runs (how fast or how much it handles, what it keeps across a restart, a crash or a
  concurrent change, the exact output, order or shape it produces, or which of conflicting sources holds), else
  NOT_RUNTIME (intent or policy the request leaves open, structure or conventions read from the code, delivery, a
  person's decision).
- M1 per output: RUNTIME questions routed `experiment`. M2: NOT_RUNTIME questions routed `experiment`. Ledger validity:
  ShipLoop's own shape check (`shiploop_navigator._check_intake_questions`).
- Rule: the sentence moves routing iff mean M1 rises by at least 1.0 from A to B with an exact one-sided permutation
  p < 0.05 over the 16 + 16 outputs, mean M2 in B is at most A's + 0.5, and B has at most one more invalid ledger than A.
  Otherwise the candidate keeps the shipped route text.

### XR result (scores-routing.json; 32 of 32 outputs parsed, 8 judge calls, every question id classed)

| Arm | RUNTIME questions per output | of them routed `experiment` (M1) | share routed | NOT_RUNTIME routed `experiment` (M2) | questions per output | invalid ledgers |
|---|---|---|---|---|---|---|
| A (shipped) | 2.56 | 0.25 | 10% | 0.25 | 11.75 | 0 |
| B (route sentence) | 3.19 | 1.06 | 33% | 0.00 | 12.0 | 0 |

- The rise in M1 is 0.81 per output, exact one-sided p = 0.0035; M2 falls by 0.25; no invalid ledger. The rule asks for a rise
  of at least 1.0: **not met**, so the candidate keeps the shipped route text. The sentence works in the direction meant and
  over-routes nothing, but two-thirds of the questions the judge calls RUNTIME still take `inspect`.
- Per case, M1 A -> B: ticket-assignment 0 -> 0.75, ticket-escalation 0 -> 1.5, ticket-import 0.75 -> 2.0, user-listing
  0.25 -> 0.
- Seen on the way: on ticket-import the shipped intake already raises the deciding facts (request-size limits, per-ticket
  storage I/O against the 10-second bound, atomicity) in every sample, and routes the timing question to `experiment` in all
  four arm-A samples; concurrency and restart questions mostly take `inspect`.

## XI. A case whose deciding facts only running settles, and a futility-gated live A/B (pre-registered)

- Case `ticket-import` on fixtures/node-tickets, unchanged (pin 5652a97375d0). Request: ticket-import-prompt.txt
  (POST /tickets/import of up to 5000 tickets, all or none, answered within 10 seconds). Facts it depends on and does not
  name, each in the base: requests over MAX_BODY_BYTES (64 KiB by default; src/config.js, README) are refused, so a
  5000-item body is refused unless the route accepts it; the data file is rewritten whole after every change
  (docs/operations.md, decision 8), so creating 5000 tickets one by one takes minutes; a create audits and enqueues a
  notification, which an all-or-nothing import must not leave behind; numbers are given out in order.
- Held-out acceptance (checks/ticket_import_accept.py) calibrated per SPEC ("A brownfield case") before any live run:
  base fails every fail-to-pass check and passes the pass-to-pass ones; a reference passes all; an alternative passes
  all; each targeted defect fails exactly its checks.
- Runner: `run.py --case ticket-import --host codex --model gpt-6.1-terra --effort high --source checkout --timeout
  7200`, hooks on, output ~/e2e-runs-xr/20261031/<arm>-ticket-import-s<n>, one lane (port 4180).
- A run passes when every acceptance check passes.
- Stage 1, futility: three arm-A runs (ShipLoop at main, its own run.py, the case added). If all three pass, stop: with
  A passing at least 3 of 6, even 6 of 6 for B gives p >= 0.09, so the adoption rule below cannot be met. Verdict: no
  measured headroom for a required experiment route on this case.
- Stage 2, only when an A run fails an acceptance check: build the candidate (XR's route text if XR adopts it; a
  research duty and a research gate: each intake question routed `experiment` is probed, with its command and saved
  output, or left open with the item that settles it), run 3 more A and 6 B, interleaved. Adopt iff B's pass rate beats
  A's with an exact one-sided permutation p < 0.05 (6 vs 6), no B run fails a pass-to-pass check A passes, and the probe
  commands appear in the host event stream of at least 4 of the 6 B runs. Secondary: minutes, send-backs.
- Amendment, 2026-10-31 13:45, after A s1 and before any arm-B work: A s1 delivered nothing. ShipLoop paused at
  step-plan: its plan had recorded "Persisted 5000-ticket response can meet 10 seconds" as an open assumption due at W1
  (reason "Candidate does not exist"), the step-plan gate asked for an expectation checked on the unchanged base, and the
  model judged that impossible and stopped. Intake had routed Q2 ("What limits and costs affect a 5000-ticket
  request?") to `experiment`; nothing probed it. No acceptance was observed, so A s1 is a non-pass; the pre-registration
  named neither this nor a run that delivers nothing. Read as written in spirit: the futility stop needs three passes,
  which can no longer happen, so Stage 2 opens, with the candidate as registered (the shipped route text, since XR did
  not adopt the sentence; a research duty and a research gate for each intake question routed `experiment`). The
  adoption rule is unchanged. A run that delivers nothing counts as a non-pass in either arm.
- The live hold: other sessions record an owner hold on new live E2E cycles (d9fefb11, 488ffbd9, 8975a5bc). The owner's
  go for this live work came in this session ("Do all", to a plan naming a live A/B of 6 runs per side); the runs are
  confined to this gated design.

## FX. Settling an open item through an executed criterion (pre-registered 2026-10-31 14:40, before any FX run)

- Why: replaying the 205 traced runs, the step-plan rule that turns each open plan assumption due at an item into an
  expectation (checked on the unchanged base) refused in 15. In 4 the assumption was about what exists and the
  expectation was a real experiment; in 11 it was about what the item builds or deploys, and 10 were met with a check
  that settled nothing while 1 (XI A s1) stopped. The fix (branch fix/assumption-settled-by-criterion-ee94d1, fd8f9239)
  lets an executed criterion cite the item in `from`, offers that row in the template, and keeps the expectation route.
- Arms on ticket-import, Codex `gpt-6.1-terra` at high, all tools, `--source checkout`, one lane: P = ShipLoop as on main
  7f565994 plus the case (exp/xi-case-on-main, 7167c284); F = P plus the fix (exp/xi-fix-on-main, aa99fdff). Four runs
  each, in the order P F F P P F F P, after XI's own runs end; outputs ~/e2e-runs-xr/20261031/<P|F>-ticket-import-s<n>.
- Measures per run: every held-out check passes; ShipLoop's end state; each open plan assumption due at an item and the
  route its step plan cites it by (criterion, expectation, none); this rule's refusals in the trace; minutes.
- Rule: adopt the fix iff (1) F passes at least as many runs as P, (2) in the F runs whose plan leaves an item open, the
  step plan cites it through a criterion in at least 3 (with fewer than 2 such runs the route is not exercised live,
  and adoption rests on the replay and (1)), and (3) the quick tier passes on the fix. This is a no-harm and
  mechanism test, not a superiority test: a stall like A s1 is rare, so 4 runs a side cannot show its rate falling.
- Note, 14:30, before any FX run: the fix's quick tier failed one suite (shiploop-package-integrity: the new paragraph took
  references/inner-loop.md over its 8,192-byte bound). The paragraph became a reworded sentence (dcf98cb6, no script
  change), so F is rebuilt at 52feffd0 = aa99fdff + dcf98cb6, and FX waits for the rerun tier to pass.

## XI interim and FX status (2026-10-31 15:15)

| Arm | Runs scored | Pass every held-out check | Stopped in planning | Research probes recorded |
|---|---|---|---|---|
| A, ShipLoop as on main 02a215e9 | 5 | 3 (s2, s3, s5) | 2 (s1, s4: the open timing assumption had to become an expectation checked on the unchanged base) | n/a |
| B, A plus research probes | 5 | 5 | 0 | 0 of 5 (s1, s2, s5 recorded the question open, "the endpoint does not exist yet"; s3, s4 routed nothing to experiment) |

- Decided before its last runs: XI does not adopt the candidate. With A at 3 passes, even 6 of 6 for B gives p >= 0.09,
  and the probe clause (probe commands in the event stream of at least 4 of 6 B runs) has 0 so far. B's clean record
  does not come from probing; the likelier reading is that B's runs met the same rule with a check of their own (an
  expectation citing the open item, 5 of 5) where two A runs stopped.
- B s6 was cut off at 15:11 when the operating Claude Code session restarted and its background jobs ended (the harness
  died mid-run; its orphaned progress viewer was stopped). It is an infrastructure stop, not a subject result: excluded,
  and replaced by B s7 from the same candidate checkout. A s6 follows, then FX.
- Fix 1 (an open item settled by an executed criterion) is published in skill-craft 2.27.0 / ShipLoop 1.26.0 at the
  owner's word ("Merge to main and publish") before FX ran, with a No-E2E-Round trailer on its two commits; FX is its live
  check. Release eeb433d5, published 15:13 over main 2bfe9334 after CI passed there.


## XI final and FX result (2026-10-31 17:15)

XI final (score_xi.py on the rejected candidate's branch; empty learning commit 2ae6200e): A 3 of 6 pass every held-out
check, B 6 of 6 (B s7 replaced the infrastructure stop B s6), exact one-sided p = 0.0909; probe commands are in the
host's event stream in 1 of 6 B runs (s7). Not adopted. All three A failures are the step-plan stall this study's fix 1
is built to remove (s1, s4, s6); whether it prevents the stall live is unmeasured (corrected 2026-11-01: this said
"removes"; see Calibration).

FX (scores-fx.json; 8 of 8 runs scored, in run order):

| Run | Held-out checks | End | Minutes | Open item: route and the command that settles it | Refusals of the rule | Send-backs |
|---|---|---|---|---|---|---|
| P s1 | 13/13 | PASS | 11.9 | A2 expectation: `node --version` | 0 | test-spec |
| F s1 | 13/13 | PASS | 10.4 | A2 criterion: `node ../run/scratch/import-probe.js` | 0 | implement |
| F s2 | 13/13 | PASS | 11.5 | A2 criterion: `focused and regression suite` | 0 | none |
| P s2 | 13/13 | PASS | 16.1 | A2 expectation: `node -e "const … assert.equal(r.status,404)}).catch(e=>{c` | 1 | test |
| P s3 | 13/13 | PASS | 12.9 | A2 expectation: `node --test test/store.test.js` | 0 | implement |
| F s3 | 13/13 | PASS | 11.0 | A2 criterion: `timed HTTP test and npm test` | 0 | none |
| F s4 | 13/13 | PASS | 14.4 | A2 criterion: `timed node:test` | 0 | none |
| P s4 | 13/13 | PASS | 15.3 | A2 expectation: `node -e "require('./src/store')"` | 0 | none |

- Rule: (1) no harm: F passes 4 of 4 against P's 4 of 4: met (as registered; at 4 runs a side this is no harm seen,
  not harm ruled out: see Calibration); (2) mechanism: every F plan leaves the timing item (A2)
  open and every F step plan cites it through an executed criterion (4 of 4; 3 needed): met; (3) the fix's one
  quick-tier failure (package integrity) was fixed in 035b3a41, and the full CI tier passed on the release commit
  eeb433d5 (run 41247212349): met. **Fix 1 is adopted**; it shipped in 2.27.0, so nothing is reverted and no release
  follows. The rule was settled after F s4 (F 4 of 4 cannot be beaten); P s4 ran to complete the pre-registered
  record.
- What settles the item: every P step plan meets the rule with an expectation that times nothing (`node --version`; the
  import route answers 404 on the base; the existing store's tests; a check that the store module loads), and P s2 needed one refusal of the rule to
  get there. Every F step plan cites a criterion its own tests confirm after the build: a scratch probe timing 5000
  persisted imports at implement (s1), or the focused suite's timed 5000-ticket test (s2, s3, s4).
- Refusals of the rule: P 1, F 0. No run stalled in either arm. Mean minutes P 14.1,
  F 11.8 (exact one-sided p 0.086) (descriptive; the rule claims nothing about time).

Contrary evidence:
- The test stage writes a timed 5000-ticket test in both arms (P s1 `TC_SCALE`, F s1 `TC-2`, F s2 `TC_4`), because the
  spec carries the 10-second requirement: the route changes what the step plan records as settling the item, and by
  design gives an open item about the built code a route that can be met, not what gets tested. Neither arm stalled, so
  this round does not show it preventing a stall (corrected 2026-11-01: this said it "removes the stall path").
- XI's stall (3 of 6 runs of 02a215e9) did not recur in P (7f565994), whose step-plan `from` sentence c2da4604 had
  reworded (fix 11 of the stage-prompt review), so this round shows no stall rate either way.
- F s1's one send-back (implement: "C1 and C2 require a new test file which the implementation contract forbids
  writing until test stage") came from a step whose Proof, `npm test`, cannot run the item's new criteria at implement.
  C1, which has no `from`, had the same fault; the proof-order refusal reads only test paths a Proof names, so it does
  not see a Proof that names none. It is a step-plan gap of its own, not a cost of fix 1.

Unknowns: one case on one base, one subject and effort, 4 runs a side; how often the stall occurs at all on the wording
P ran (2.26.2, after c2da4604), and so whether fix 1 prevents any live stall (corrected 2026-11-01: this read "on
2.27.0's baseline wording"; 2.27.0 carries fix 1, and P ran 2.26.2).

## Calibration (2026-11-01)

Rechecked when the owner asked "Are you certain about the conclusions?". No new runs.

The numbers hold:
- score_fx.py, run from a scratch copy over `~/e2e-runs-xr/20261031/[PF]-ticket-import-s*`, reproduces scores-fx.json.
- stats.permutation_p reproduces FX's minutes p (0.086) and XI's pass p (0.0909).
- Every run used its arm's commit, and the two FX arms differ only by fix 1's five files.
- Read from each run's last accepted step plan directly, not through the scorer: F cites A2 through executed criteria in
  4 of 4 runs, P through expectations in 4 of 4.

Two readings claimed more than 4 runs a side carry:
- No harm. Condition (1) is met as registered, but it shows no harm seen, not harm ruled out. A true pass rate of 70%
  still gives 4 of 4 about 24% of the time (0.7^4), and 4 of 4 rules out only rates below about 47% (one-sided 95%,
  0.05^(1/4)).
- The stall. Fix 1 removes the dead end by design: the step-plan gate now accepts an executed criterion for an open item
  about what the item builds (test/shiploop-callback-contract.test.py). Its live benefit is unmeasured:
  - XI's baseline (02a215e9, which lacks c2da4604) stalled in 3 of 6 runs; P (7f565994, after c2da4604, without fix 1)
    stalled in 0 of 4. That is exact one-sided p 0.17 (20 of 120 splits), and the two bases differ by more than fix 11.
  - So fix 1's gain over fix 11 is not measured.
  - Measuring it would be expensive. Suppose the stall still hit 1 run in 4 without fix 1, and never with it. At 15
    runs a side, a one-sided Fisher test reaches p < 0.05 only about half the time (power 0.54); 80% needs about 25
    runs a side (power 0.79).
  - The cheap stand-in, counted the same day from the saved runs (docs/experiments/proof-coverage-replay-20261101, Q2;
    observational):
    - no run stopped at step-plan under fix 1's wording: 0 of 14 runs with an open item due (0–23%);
    - before fix 11, 4 of 33 stopped (12%);
    - one-sided p 0.23.

The decisions stand. Fix 1 stays: its rule was met, and it replaces checks that settle nothing. XI and XR stay not
adopted.

Corrected in place on this date:
- the XI-final sentence;
- condition (1)'s line;
- the first contrary-evidence bullet;
- the unknowns line.

The same corrections are in the FX round entry of test/shiploop_e2e/LEARNINGS.md and in
docs/shiploop-question-driven-planning-journal.md (E14, E15, E16, F22).

## Closed (2026-11-01)

The candidate this study left, a check that each step's Proof can run its own new criteria, was replayed and then built
in its narrow form: rule C of the proof-order refusal, released in skill-craft 2.27.4 / ShipLoop 1.26.4
(docs/experiments/proof-coverage-replay-20261101, journal E17 and E18). The study closes at journal E21. On the runs made
since the release, rule C neither fired nor refused any of 147 judged plans. Fix 1 and rule C are kept, and XR and XI
are still not adopted. Characterization tests stay on hold. The conditions for reopening are in that folder's README.
