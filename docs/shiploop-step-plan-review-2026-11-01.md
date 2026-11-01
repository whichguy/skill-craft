---
Status: one change built, tested hermetically (§5) and live on Codex Terra 6.1 xhigh (§7a: 6 deliveries, 20 step-plan slices; a
  wording fix, 45153684, came out of it); ticket-import deliveries pending; release and §8 are the owner's
Opened: 2026-11-01
Consumer: the owner, who asked to make step planning as effective and efficient as possible; later, a session that changes
  the step-plan stage reads §3 for what it costs and what goes wrong, and §6 for what was considered and not built.
Journal: docs/shiploop-question-driven-planning-journal.md, E19 (findings F26-F30) and E20 (F31, F32); E17 and E18 there are
  another session's concurrent proof-coverage study
Evidence: docs/experiments/step-plan-review-20261101/ (corpus, scripts, JSON lines; README there)
---

# Step planning: how effective and efficient it is, and what changed (2026-11-01)

The owner asked (2026-11-01) to revisit the step-planning stage and make sure it is as effective and efficient as
possible. This review measures the stage over every saved run that has a trace, finds where its plans fail later and
what the stage costs, and changes what the evidence supports.

## 0. The answer in brief

- **Cost.** Step-plan takes a median 11.3% of a run's elapsed time: a median 31 seconds to author and 28 to review
  on Codex Terra 6.1, and 3.0 and 2.1 minutes on DeepSeek flash, Grok 4.7 and Sonnet 5.5 (up to 9 and 10). Inside its
  loop, refusals fell from 57 in
  53 plans (ShipLoop 1.24.1-1.25.0) to 25 in 44 (1.25.1-1.26.1) after the 2026-10-31 prompt fixes. The authoring loop
  is no longer where the time goes.
- **Effectiveness.** 50 of 178 step plans (28%) came back to step-plan from a later stage. Each send-back cost a median
  0.9 minutes of downstream work plus 0.8 to redo the plan on Terra, and 7.2 plus 4.4 minutes on average on the other
  models. On the current ShipLoop (1.25.0 and later) 19 send-backs remain, and the largest class, 8 of 19, is a plan
  that names more executed criteria in a focused command than it lists test IDs. Test-spec writes one case per
  focused ID and a case names one criterion, so one criterion has no case. The proof-order refusal of 1.25.0 removed
  its own class: 13 send-backs before it, none after.
- **Root cause.** The step-plan contract never said that each criterion needs its own ID. Since 8dee00e0 (1.26.0) its
  result template has shown a focused row with three criteria and two IDs whenever an open item is due at the item.
  The step-plan Improve review saw 22 of the 24 short plans and the shortage survived every one.
- **Change (built).** Step-plan refuses a plan that leaves an executed criterion a focused command names without a
  focused ID of its own; the template lists one ID per criterion; the duty and the Checked-by line say so. Replayed
  on all 175 accepted step plans, the rule refuses 24: the 9 that came back from test-spec and 15 that folded a
  criterion into another criterion's case. It refuses no plan whose every criterion had its own case.
- **Not built.** A gate for a Proof that runs unwritten tests without naming a test file: four candidate rules each
  flag Proofs that passed (§6.1), and so does the narrowest, rule S (5 of 12 flags were real); since 1.27.0 another session's narrow rule C refuses the plain-suite form by path. A Proof dry run, a
  repeatable-Proof line and changes to the step-plan Improve review are listed for the owner (§8).
- **Live (§7a, Codex Terra 6.1 xhigh).** Six deliveries passed with no test-spec send-back for IDs; 16 step-plan
  slices (A/B) and 4 more showed no extra step-plan time and no short plan. They also caught one regression: the first
  duty wording, "an ID for each criterion it names", drew IDs for searched criteria, which test-spec writes no case
  for. 45153684 narrows it to executed criteria, and SP3 confirmed the fix. At xhigh the shortage still occurs (10% of
  saved plans) but test-spec mostly folds it rather than sending it back, so the gain there is test quality.

## 1. The stage

`step-plan` is the first inner stage of each work item (`shiploop_stage_spec.STAGE_SPEC["step-plan"]`). One packet
asks for `criteria`, `steps` (each with deps, criteria and one `proof`), `test_commands` (focused, regression, check),
`expectations`, `paths` and `follows` (`shiploop_prompts.DUTIES["step-plan"]`, 12 duty items). It runs inside a
script-written Until Loop whose Work runs the callback with `check` until the gates say yes, and the first item (or a
sent-back one) gets an Improve review (rule `first-item`). Its gates are in `shiploop_navigator` (`_normalise_criteria`,
`_check_submitted_test_commands`, `_check_step_sizing`, `_check_focused_ids_new`, `_check_focused_guards`,
`_check_proof_inputs`) and `shiploop_expectations.check_step_plan`. What it records is consumed by test-spec (one case
per focused ID), validate-existing (expectations), each step's implement (its Proof) and test stage (the commands).

## 2. Method

- Corpus: 112 saved runs with a trace, 2026-10-25 to 11-01, ShipLoop 1.12.0-1.26.1. Most ran on Codex Terra 6.1 (high
  or xhigh); a few on DeepSeek v4.1 flash, Grok 4.7 and Sonnet 5.5. The cases are small: hello, user-listing,
  ticket-assignment, ticket-escalation, ticket-import, CSV report, battleship, Salesforce gym and battleship.
- Tools, read-only: `docs/experiments/step-plan-review-20261101/step_plan_review.py` (times from the trace's packet and
  cursor events; refusals; every send-back to step-plan with its result; the focused-ID rule on every accepted plan;
  the Improve passes) and `replay_proofs.py` (candidate Proof rules against each step's implement outcome). Each
  send-back was classified by reading its headline and summary (`sendback_classes.jsonl`).
- Caveats: the version mix matters, so §3 reports the current versions apart; Terra dominates; times are wall time
  between ShipLoop events, so they include the host's own overhead.

## 3. What the stage costs and where its plans fail

### 3.1 Time

| | median | mean |
|---|---|---|
| step-plan share of a run's elapsed time | 11.3% | 11.6% |
| authoring, packet to the accepting callback (178 actions) | 0.61 min | 1.16 min |
| Improve review of the step plan (157 reviews) | 0.55 min | 0.95 min |

On Terra (142 actions) the medians are 0.52 minutes to author and 0.47 to review; on DeepSeek flash, Grok 4.7 and
Sonnet 5.5 (34 actions) 3.0 and 2.1 minutes, up to 9.1 and 9.7. The review is about 45% of the stage.

### 3.2 The authoring loop

275 `check` calls and 141 refusals over 178 actions. By version: 1.24.1 28 refusals in 30 plans, 1.25.0 29 in 23, 1.25.1
6 in 15, 1.26.0 8 in 16, 1.26.1 11 in 13. The drop at 1.25.1 is c2da4604's fixes (the `from` refusals and the check row
that carried criteria). The remaining refusals cost one model turn each: an open item due here left unsettled, an
empty `criteria` or `ids` list, a Proof on two lines, a check run before the result file was written.

### 3.3 Send-backs

| Class | All versions | ShipLoop >= 1.25.0 |
|---|---|---|
| a Proof runs a test file the test stage writes later | 13 | 0 (refused at step-plan since 1.25.0) |
| the same need, naming no test file (`npm test`, unittest discovery, an Apex class, a criterion that asks for the test) | 10 | 3 |
| fewer focused IDs than the criteria a focused command names | 9 | 8 |
| a Proof command defect (quoting, a wrong API or setup, a non-portable flag) | 8 | 4 |
| a Proof that cannot run twice (a permission-set assignment) | 3 | 2 |
| IDs the runner cannot print, or a floor it cannot reach | 3 | 0 |
| a minimum regression or a case that needs a later step | 2 | 2 |
| other (a diagnostic replan; a step with no test) | 2 | 0 |
| **total** | **50** (32 from implement, 12 test-spec, 6 test) | **19** |

The ">= 1.25.0" column also counts one run of the 2026-10-31 A/B's refusal arm (1.24.1 plus the proof-order refusal).
A send-back cost a median 0.9 minutes of downstream work (step-plan accept to the send-back) and 0.8 to redo the step
plan, with its review, on Terra; 7.2 and 4.4 minutes on average on the other models (`sendbacks.jsonl`).

### 3.4 The focused-ID shortage

Test-spec writes one `test_cases` row per ID the focused commands list, each row names one `criterion`, and its gate
refuses an unlisted ID (`shiploop_expectations.check_test_cases`); its duty says "A criterion that needs an unlisted ID:
report send-back naming it". Step-plan's duty said only "focused: this item's cases with the IDs they carry", and its
template showed `"ids": ["TC-1", "TC-2"]` beside `"criteria": ["C1", "C2", *settles]` (8dee00e0), three criteria and
two IDs whenever an open item is due. The plans that test-spec sent back:

- `["TC_IMPORT"]` for C1 and C2 (ticket-import P s1, 1.25.1): "add a second focused ID to cover C2";
- no IDs at all for C1-C5 (ticket-escalation B2, 1.26.0): "Focused command lists no test IDs";
- `["TC_1".."TC_4"]` for C1-C5 (ticket-assignment, 1.26.1): "Add a fifth ID for C5".

Test-spec handled the other 15 by folding: "C2 and C3 are the same TC-7 case, because the focused IDs allow only that
one row" (battleship-scoring), "TC_6 also covers C3" (multipass A2). Each folded criterion lost its own oracle, RED
and GREEN, and at an inline step a criterion with no case leaves its step with no due case.

### 3.5 The step-plan Improve review

155 reviews, 239 passes; 62 reviews (40%) changed the plan. The non-trivial passes mostly strengthened a Proof that
asserted less than its criterion claimed, and twice found a Proof that needed an unwritten test (terra-high-user-listing,
hooks-before-ticket-escalation). They never fixed the ID shortage: 22 of the 24 short plans were reviewed. Of the 50
plans that came back (§3.3), 46 had been reviewed.

## 4. Findings

- **F26 (firm).** Step-plan is a median 11% of a run; its review is about 45% of the stage; the authoring loop's
  refusals halved after c2da4604. Evidence: §3.1-3.2, `runs.jsonl`.
- **F27 (firm).** 28% of step plans come back to step-plan. On the current ShipLoop the largest class (8 of 19) is a
  focused command with fewer IDs than its executed criteria; the proof-order refusal took its class from 13 to 0.
  Evidence: §3.3, `sendback_classes.jsonl`.
- **F28 (firm by construction; the template's share unmeasured).** The shortage comes from the contract: step-plan
  never stated test-spec's one-case-per-ID, one-criterion-per-case rule, and its template has modelled a short row
  since 8dee00e0. The shortage predates that template (it is in 1.17.0 and 1.24.1 runs), so the template is one cause,
  not the only one. Evidence: §3.4, 8dee00e0, c2da4604.
- **F29 (firm, replay).** A matching rule (each executed criterion a focused command names gets a distinct ID of a
  focused command that names it) refuses 24 of 175 saved plans: the 9 that test-spec sent back and 15 that test-spec
  folded; none whose every criterion had a case. Evidence: `replay_ids.jsonl`.
- **F30 (firm, replay).** No precise rule separates a Proof that runs unwritten tests without naming a file from a
  legitimate one: a focused command can be a hand-written check that exists before the test stage (a browser checker,
  an anonymous Apex script). Evidence: §6.1, `replay_proofs.jsonl`.

## 5. What changed (this branch)

| Where | Before | After |
|---|---|---|
| `shiploop_test_loop.criteria_without_ids` | — | the executed criteria a focused command names that cannot each get a distinct focused ID from a focused command naming them (a bipartite matching) |
| `shiploop_navigator._check_focused_criteria_ids` (at `complete`, `check` and the Improve import) | — | refuses the plan, naming the criteria and the IDs listed: "Add an ID for each (one test file can hold them all), or, for a criterion that existing tests already confirm, name it on the regression command instead" |
| step-plan template | `"ids": ["TC-1", "TC-2"]` for C1, C2 and each settling criterion | one ID per criterion: TC-1..TC-(2+n) |
| duty 5, focused bullet | "this item's cases with the IDs they carry" | "this item's cases, an ID for each criterion it names" |
| Checked-by line | "...only reruns an earlier item's test IDs or starts with a file guard" | "..., starts with a file guard, or lacks an ID per criterion" |
| `references/inner-loop.md` | — | the rule and why, under step-plan |

Tests: `test/shiploop-test-loop.test.py` (the matching, nine cases and a malformed row),
`test/shiploop-callback-contract.test.py` (the template's IDs; `check` and `complete` refuse a short plan with the
message, and the same callback accepts it with an ID added; a criterion only the regression command names needs no
ID; fix 1's test now gives its settling criterion an ID). Both new assertions fail without the change (the template
lists two IDs; `check` says yes). Change note: `changes/shiploop/focused-id-per-criterion.md` (minor).

## 6. Considered and not built

### 6.1 A Proof that runs unwritten tests and names no test file

Ten send-backs (3 on the current ShipLoop): `python3 -m unittest -v`, `npm test`, `sf apex run test --class-names
<a new test class>`, or a criterion whose "Confirm by" names the focused tests. Four rules were replayed on 376 steps
(steps flagged, by implement outcome: send-back / done / no implement): N1 the Proof is a focused command, 10/12/18;
N2 it names a focused ID, 7/11/23; N3 it is the regression command while its criteria are focused ones, 4/2/3; N4 it
names the stem of a new test file, 7/30/11. Limited to the first step, N1 is 8/5/3. The "done" Proofs include legitimate
ones (a supplied browser checker, an anonymous Apex script that prints its IDs), so no rule is precise enough to gate on.
The 2026-10-31 study reached the same answer for the prompt route (X4, journal E8).

Side replay (2026-11-01, after SP1's xhigh csv-report s1 hit the class live: S1's Proof `python3 -m unittest -v && rg -n
"CSV" report.py`, unittest exiting 0 on zero tests): rule S, the narrowest generic form, flags a first step whose Proof
holds, as one whole shell segment, a focused command none of whose IDs any tracked file of the item base holds
(`git grep -w -F` in the recorded lint item-base tree; `replay_rule_s.py`). Over the 171 plans with a recorded base it
flags 12: 5 went on to a proof-order send-back (2 of them Rule A already refuses), 5 passed implement, 1 blocked and 1
was sent back for another reason (`grep -P`). Exempting a command whose own text holds its IDs moves nothing: the
passing ones are supplied checkers (`gym-ui`, `battleship-ui`), a script in the run folder and Salesforce test runs,
which print IDs no tracked file holds. Not built (F30).

Another session studied the same class at the same time (planning journal E17 and E18,
docs/experiments/proof-coverage-replay-20261101/) and shipped a narrow rule in ShipLoop 1.27.0, rule C of the
proof-order refusal (`shiploop_item_scope.proof_order_refusal`): a Proof that is a generic suite command (`npm test`)
is refused when an executed criterion of its step names, in its Confirm by, a test path the base lacks (3 of 365 judged
plans in sample, none on 42 held-out runs). It does not reach a test named by identifier (a unittest name, an Apex
class) or a compound Proof, so SP1's csv-report s1 above would still pass it; that session's E17 measured the misses at
about 10 minutes in 365 plans.

### 6.2 Others

- A Proof dry run at step-plan: the 4 current Proof defects are a JavaScript syntax error inside shell quotes, wrong
  quoting that still parses, a wrong method name and a wrong state transition; `bash -n` catches none of them, and
  running a Proof at step-plan can deploy or write.
- A Proof that must run twice: all 3 are `sf org assign permset`. A generic duty clause ("ShipLoop runs it again at
  done, so a command that creates state checks for it first") would cost about 90 characters of the step-plan head,
  which has 34 to spare after §5's change (19,966 of 20,000); the Salesforce E2E work owns that case.
- Empty `criteria` and `ids` lists: refusing them costs a turn (6 times on 1.26.x); accepting them as absent saves
  seconds and was not worth a change.
- The step-plan Improve review: about 45% of the stage; it changes 40% of plans and misses the structural defects.
  Whether to keep it per item is the owner's (§8, and F1 of
  docs/shiploop-planning-speed-and-caps-plan-2026-10-28.md).

## 7. Unknowns and next

- Live check SP1 (pre-registered here before any run; launcher `docs/experiments/step-plan-review-20261101/
  launch_sp1.sh`): this branch from its checkout, Codex Terra 6.1 high, the run.py line of FX; ticket-import 3
  samples (its open item due at W1 is where the template showed three criteria and two IDs; 3 send-backs and 1 fold in
  19 runs of 1.24.1-1.25.1), csv-report 2 and hello 1 (each had a send-back for missing IDs on 1.25.x). Predictions:
  (1) no test-spec send-back for missing IDs; (2) where a draft is short, a step-plan `check` refusal names the criteria
  and a later draft passes; (3) every accepted plan gives each executed criterion a focused command names an ID; (4) the
  hidden checks hold. A test-spec send-back for missing IDs, or a hidden check lost to the change, falsifies it. Step-plan
  minutes and refusals are reported beside the corpus, descriptively.
- Side experiment SP2 (the owner, 2026-11-01: "You can do side experiments as needed if that would help"; pre-registered
  here before any slice): SP1's ticket-import samples wait on port 4180, held by another session's round, and a whole
  delivery measures step-plan only indirectly. SP2 runs the step-plan stage alone: `slice.py --stop-after test-spec`
  (seeded at step-plan, the item's Improve review on, no product server, no port lease), Codex Terra 6.1 high, arm B =
  `origin/main` at this branch's base e81fdb55 (a detached worktree), arm T = this branch; step cases `tickets-assign`
  (an API item of several behaviours, the family of the live ticket-assignment shortage) and `stand-in-rules` (a
  module of many rules), 4 slices per arm per case, order B T T B per case. Launcher and scorer:
  `docs/experiments/step-plan-review-20261101/launch_sp2.sh`, `score_sp2.py`. Measures per slice: whether the
  accepted plan leaves a criterion without an ID (`criteria_without_ids`); refusals by the new gate (arm T: how often a
  draft was short); the test-spec outcome (done, a send-back about IDs, another send-back); step-plan authoring and
  Improve minutes; test-spec cases per criterion. Predictions: arm T 0 short accepted plans and 0 test-spec send-backs
  for IDs; arm B some short plans (14% of saved plans overall); arm T's median step-plan minutes within one minute of
  B's. A test-spec send-back for IDs in arm T falsifies the change, as in SP1. SP2 is descriptive at 8 slices per arm;
  SP1 stays the release round.
- Amendment, 2026-11-01 07:47 (the owner: "For using a test harness and runner we want to use codex Terra 6.1 at
  xhigh"): SP1 and SP2 run on Codex Terra 6.1 xhigh, with the designs, predictions and scorers above unchanged, into
  `~/e2e-runs-sp/20261101/sp1-xhigh` and `sp2-xhigh`. Made at high before the amendment and kept as a pilot, not
  pooled: SP1 hello s1, csv-report s1 and s2 (all PASS, 9.0, 11.6 and 15.0 minutes; no test-spec send-back for IDs,
  no refusal by the new gate, every accepted plan giving each executed criterion an ID; csv-report s2's one send-back
  was test-spec reading a module that fails to load on the empty base as no behaviour-specific RED, and step-plan
  resubmitted unchanged, citing the test-loop guide). SP2's first four high slices were stopped about two minutes
  in, before any step plan was accepted, and are not scored. SP1's ticket-import samples had not started.
- SP3 (pre-registered here before any slice, 2026-11-01): SP2's arm T stand-in-rules s2 named two searched
  documentation criteria on the focused command with IDs, and test-spec sent it back (it writes no case for a searched
  criterion); b8d32033's duty line said "an ID for each criterion it names". 45153684 says "each executed criterion".
  SP3 runs that commit alone: stand-in-rules, 4 slices, the SP2 slice line (Codex Terra 6.1 xhigh, `--stop-after
  test-spec`), `launch_sp3.sh` into `~/e2e-runs-sp/20261101/sp3-xhigh`, read by `score_sp2.py`. Predictions: no
  test-spec send-back about IDs or a searched criterion's case; no accepted plan short of IDs. A repeat of the
  searched-criterion send-back means the wording fix does not hold.
- The 15 folded plans gain cases, so test-spec and the test stage write more tests; the time that adds is unmeasured.
- DeepSeek flash and Grok are a small share of the corpus; their send-back costs are means of 5.

## 7a. Live results (2026-11-01, Codex Terra 6.1 xhigh unless marked)

| Round | ShipLoop | Samples | Outcome | Test-spec send-backs for IDs | Refusals by the new gate | Accepted plans short of IDs |
|---|---|---|---|---|---|---|
| SP1 pilot, **high** | b8d32033 | hello 1, csv-report 2 | 3 of 3 PASS (9.0, 11.6, 15.0 min) | 0 | 0 | 0 |
| SP1, xhigh | b8d32033 | hello 1, csv-report 2 | 3 of 3 PASS (11.5, 15.3, 21.8 min) | 0 | 0 | 0 |
| SP1, xhigh | 45153684 | ticket-import 3 | pending (port 4180 held by another session's round) | | | |
| SP2 arm B | e81fdb55 (main) | tickets-assign 4, stand-in-rules 4 | 8 of 8 reached test-spec done | 0 | — | 0 of 8 |
| SP2 arm T | b8d32033 | tickets-assign 4, stand-in-rules 4 | 8 of 8 | 1 (IDs for searched criteria) | 0 | 0 of 8 |
| SP3 | 45153684 | stand-in-rules 4 | 4 of 4 | 0 | 0 | 0 of 4 |

- Step-plan minutes (authoring plus the Improve review, median): SP2 B 2.17, T 2.25; SP3 2.50. The change costs no
  measurable time.
- The one arm-T send-back (stand-in-rules s2) came from b8d32033's duty line "an ID for each criterion it names": the
  plan named two searched documentation criteria on the focused command with IDs, and test-spec, which writes no case
  for a searched criterion, sent it back. 45153684 says "each executed criterion"; SP3 had no such send-back, and its
  one plan that still named searched criteria on the focused row gave them no IDs and passed test-spec (as the 3
  saved plans that did so before this change had).
- SP2 arm B produced no short plan at xhigh, against the pre-registered "some". The saved corpus explains it: Terra
  xhigh plans were short 7 times in 67 (10%), and test-spec sent back only 1 of them, folding the rest; Terra high 8 in
  75 (11%), 7 sent back. At 10%, 0 of 8 happens 43% of the time. On the owner's runner the rule's gain is mostly test
  quality (each executed criterion gets its own case, RED and GREEN) rather than fewer send-backs.
- Other send-backs seen, none about IDs: SP1 pilot csv-report s2 (test-spec read a module that fails to load on the
  empty base as no behaviour-specific RED; step-plan resubmitted unchanged citing the test-loop guide, and it passed);
  SP1 xhigh csv-report s1, twice from implement: first S1's Proof `python3 -m unittest -v && rg -n "CSV" report.py` ran
  the focused suite before any test existed (unittest exit 0 on zero tests; §6.1's class), then implement objected that
  the criteria's "Confirm by: unittest TC_1-TC_3" named tests it may not write (F31).
- Slice verdict: every slice reports `no_overshoot` FAIL because ShipLoop accepts validate-existing by script in the
  same callback as test-spec; SP2 and SP3 read only step-plan and test-spec, so it does not bear on them.
- Evidence: `sp2_scores.jsonl`, `sp3_scores.jsonl` (score_sp2.py); SP1 rows in test/shiploop_e2e/baselines.jsonl and the
  run folders under `~/e2e-runs-sp/20261101/` (pilot at its top level, `sp1-xhigh`, `sp2-xhigh`, `sp3-xhigh`).

F31 (interim, three live cases): implement reads a criterion's "Confirm by" test as something it must run, though the
test stage writes that test after implement (SP1 xhigh csv-report s1; F-ticket-import-s1 and B-ticket-import-s4 of the
2026-10-31 rounds). Implement's done-when says each criterion is "shown by a command or file after the last edit" and
its duty item 3 says the item's other checks belong to the test stage. A candidate fix, not built: the done-when names
the step's Proof as the implement-time confirmation and the criterion's tests as the test stage's. It needs its own
check; three cases in about thirty recent runs is too few to measure in one round.

## 8. Decisions for the owner

1. Release this change after its live check (routine under the 2026-10-28 rule once the preflight and CI pass).
2. Whether the step-plan Improve review should keep running for every first and sent-back item, given F26 and §3.5
   (held for F1's three-arm measurement).
3. Whether to add the repeatable-Proof clause (§6.2), which would take the step-plan head past its print bound unless
   another line is cut.
4. Whether to pursue F31 (§7a): implement's done-when naming the step's Proof as its confirmation, so a criterion's
   Confirm-by test (written at the test stage) no longer reads as due at implement; it would need its own live check.
