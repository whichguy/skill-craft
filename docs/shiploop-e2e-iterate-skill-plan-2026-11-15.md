# ShipLoop E2E iterate skill: name, effectiveness, and what generalizes (2026-11-15)

**Status: plan and retained learning.** No code changed and no skill built. Building the skill waits on the owner's go
(section 6). `test/shiploop_e2e/LEARNINGS.md` is deliberately untouched: a commit touching it counts for the release gate as
an E2E round for every earlier ShipLoop commit (3423e21801165d86c21e1d9e59d5c55d130bff66 says so), and nothing here measured a
ShipLoop change. The consumer of this file is the owner (the go/no-go and the open decisions) and the session that builds the skill.

## The request

Owner, 2026-11-15, verbatim in substance: a runner in the E2E harness that (1) kicks off a ShipLoop run, (2) lets it go through its
stages, (3) evaluates effectiveness and efficiency by deeply inspecting all stages, files and journals, and (4) uses higher-logic
advisors to evaluate the results and look for improvement, then repeats. Asked whether this already exists, whether it can be
called, and whether it can get into a self-improving loop; later, whether the skill's name is right, what else would make it more
effective, and what generalizes versus what is specific.

## History read first (owner decision of 2026-10-30, AGENTS.md)

- 44e9a60d8b6cd646c73412877097c4e872cbb6b1 (2026-11-08): the role split (Sol medium, Astra high). Kept from it: a resolved model and
  effort must reach each launch's argv including native children; explicit overrides and recorded identities stay authoritative; a
  profile change starts a new baseline cell.
- db47982bcd9faf553041c26958abecd402002963 (2026-11-10): the driver moved to Grok 4.6 xhigh; reviewer, judge and improver did not move.
- 7fb5ba64f019230c24b5f3099d4154357dc6891f (2026-11-15, earlier today): the improver is Sol 6.1 at max, or Sonnet 5.5 at max with
  `--improver-host claude` (`hosts.ROLE_EFFORT`). Unmeasured preference, not a gain.
- 3423e21801165d86c21e1d9e59d5c55d130bff66 (2026-11-01): the only A/A calibration. Codex gpt-6.1-terra at **high**, ShipLoop 1.27.0,
  `csv-report` and `seat-reservations`, 4 + 4 runs a case. One build's processed tokens span 17.7M to 44.1M (2.5x) and 22.1M to 50.4M
  (2.3x). At 3 attempts per arm, 0.45 on tokens keeps false calls at or under 10%; the stated 0.25 calls noise a change in 35.7% and
  27.7% of re-deals. Its author listed "high, not xhigh" and "two port-free cases" as limits.
- 551a951f038a01dc917ebc86083c94aa4487530f (2026-11-01): `cycle.review_all` assesses an incomplete review again, up to three times,
  because 2 of the 9 judgments seen in that work were invalid (2 of 6 in the restore pilot). Quality evidence in that pilot was
  decisive (accuracy 0.0 control, 1.0 candidate); one invalid judge answer alone turned a PROMOTE into UNDECIDED.
- 24f2f44a660eb30f67356f4d48456dacc2269ea3 (2026-11-15), E25: a stage-level pilot (10 samples, a registration with ten predictions)
  could not reproduce the real problem; reading the runs' upstream records and three real-flow runs ended after discovery found the
  rule was lost at house-style capture (3 of 3 against 0 of 3). The cheapest valid instrument was the real case run to the stage.
- `LEARNINGS.md` "Closed loop review: what a cycle costs, what is still unknown" (2026-10-31) and
  [docs/shiploop-e2e-closed-loop-plan-2026-10-30.md](shiploop-e2e-closed-loop-plan-2026-10-30.md): about 38 model sessions a cycle at
  3 attempts on two cases; D1 (tolerance and attempts), D3 (cycle limits) and D4 (review every attempt) are the owner's.

## 1. Does it exist? Yes, as two script paths; no named skill launches either

Verified at origin/main f36332e97f361dab32147f95141324e533dbc12a.

- **Exploration loop**: `test/shiploop_e2e/iterate.py` (`main`). One worktree and branch **per invocation**, reused by every
  iteration. Per iteration: build the worktree's plugin; `run.py` the case; `review.review` (Astra high); `judge.judge` (a fresh judge)
  admits findings; commit LEARNINGS, the Run Review export and learning records; the improver edits the candidate; quick tier.
  It stops at `--iterations`, after two scoped clean passing reviews, when the improver commits nothing twice, on a boundary
  crossing or out-of-scope edit, on a red quick tier, when the run never reached the skill, or when frozen evaluator inputs changed.
  `iteration-result.json` says `qualification` is `unevaluated` or `comparison_required`, `publication` `not_performed`,
  `learning_exhausted` false.
- **Qualified loop**: `iterate.py --qualify` runs `cycle.loop`. `learning_records.select` offers one admitted record (else `cycle.explore`
  opens some); `cycle.qualify` builds one candidate, purpose-checks it, registers a `promotion/5` epoch (candidate against the tip, the
  exposing case and an **optional** generality case; without one the decision says its claim covers the exposing style only, SPEC
  "Qualified iteration") and `epoch.decide` decides. PROMOTE advances the tip; DROP or UNDECIDED parks the candidate under
  `refs/shiploop-loop/<loop>/<record>`. It stops after `NON_PROMOTE_STOP` = 2 cycles in a row without PROMOTE (a D3 *proposal* in the
  code comment, not an owner decision), on a boundary crossing, or when no admitted record remains after exploring.
- **Evaluator boundary**: `boundary.candidate_path` lets the improver change only `skills/shiploop/`, `changes/shiploop/` and ShipLoop's
  own tests and fixtures. Held-out files are withheld and its tool calls are searched for their names. SPEC says it plainly:
  "A tool call that names a held-out file is detected; a read that never names the file is not." This is not read isolation.
- **Ledger**: `learning_records.current` folds events in time order. 24 records, 76 events: owner 9, deferred 6, admitted 4, open 2,
  verified 2, refuted 1. Only 2 of the 4 admitted are selectable by a cycle: LR-20261031-8d97e7 (found on the hosted
  `gym-membership-salesforce` case, so measuring it needs that org) and LR-20261108-4bc6cb (found on `roundtable-agent-work`). The
  others are minor (LR-20261030-8ff7a9) or target the harness (LR-20261031-382fba). A qualified loop started on another case would
  explore first.
- **Decisions on record**: five decision events on three records, all on `hello-hook-continuation`. LR-20261030-5dce01 PROMOTE
  (2026-10-31, no calibration recorded) is the one discovery. LR-20261101-1b4675 UNDECIDED then DROP came from `closed-loop-pilot`
  epochs. LR-20261101-58f651 UNDECIDED then PROMOTE came from `closed-loop-restore-02`: its record reads "restoring the qualified
  missing-completion hook to a build without it must be promoted", the control lacked the hook by design, and the final decision
  followed fresh assessments of two attempts whose judge answers were invalid. These show the mechanism works; they are not a yield rate.
- **Neighbouring skills**: `shiploop-e2e-audit` bundles an older harness (114 tracked files; its `run.py` is 1,658 lines against 5,082
  in `test/shiploop_e2e/run.py`; the README calls it "the separately installed Grok-only audit") and treats an improvement campaign
  as manual checkpoints. `shiploop-run-review` turns one run into the Run Review page; `iterate.py` only prints its `advise` command.
- **Roles now**: subject Grok 4.6 xhigh; reviewer and judge Astra high; improver Sol 6.1 max (Sonnet 5.5 max with
  `--improver-host claude`). **Caveat on the Claude host**: for the Anthropic backend `ClaudeHost.env` returns `Host.env`, the process's
  own environment plus two variables, while `CodexHost.env` and `GrokHost.env` build a throwaway HOME (`_isolated_env`). A Claude-host
  improver or subject therefore runs in the real HOME (installed plugins, global instructions, memory). Why it was left so is not
  checked here. It is one more reason Sol is the better default improver.

## 2. The name

**`shiploop-e2e-iterate`** (`/skill-craft:shiploop-e2e-iterate`). Astra (max) agreed.

- It names the script it drives (`iterate.py`) and the harness's own unit ("iteration", "qualified iteration"). The `shiploop-e2e-`
  prefix puts it beside `shiploop-e2e-audit`: it improves ShipLoop, it is not part of ShipLoop. No existing skill uses the name.
- Terms in this repository: *iteration* is one pass; *qualified iteration* or *cycle* is one candidate comparison; *exploration* is
  iterations that do not qualify; *campaign* is the owner-authorised continuing effort (SPEC "Campaign operator directive"). The docs
  also say "self-improving loop" (docs/shiploop-e2e-self-improving-loop-design-2026-10-25.md) and "closed loop"
  (the 2026-10-30 plan): three names for one thing. They are not renamed (naming alone never justifies a change); the skill's
  description carries all of them so a host matches the owner's own words.
- Rejected: `shiploop-improve*` (improve already means ShipLoop's Improve stage, the `improve` skill and the `improve-loop` skill);
  `shiploop-self-improve` (the same collision; Astra notes self-improving systems can contain separate evaluators, so the weaker
  argument is that it hides the improver; the collision is the real one); `shiploop-e2e-loop` ("loop" is ShipLoop's own name).
  `shiploop-e2e-campaign` is the one serious rival, because the skill's central duty is the campaign contract (section 3). It loses
  on the script's name and on what the owner types ("iterate", "self-improving loop"); revisit if the skill ends up only operating
  campaigns across many invocations.

## 3. What the skill is: the operator of the SPEC's campaign directive, not a launcher

The decisive requirement the first draft missed is already in SPEC "Campaign operator directive" (owner, 2026-10-31): a script stop
ends its invocation; a cap, a non-promotion streak, empty findings or a missing measurement does not establish exhausted learning.
At each checkpoint the operator inspects the **full** scoped backlog (not the truncated reviewer view) and the coverage map,
reconciles related findings by hypothesis, picks the smallest discriminating experiment, continues within recorded authority, and
reports convergence only within a named scope or stops with a blocker and a reopening condition. Without this the skill would run
`iterate.py`, stop at the first script stop and call it done. The old Grok-only audit skill holds an earlier form of this
("Campaign checkpoint"); the main harness has none.

Proposed contract (each duty comes from an existing source; nothing here is a new gate):

1. Bind to an explicit skill-craft checkout and refuse elsewhere; use the main harness (`test/shiploop_e2e`), not the audit skill's
   bundled copy.
2. Preflight: AGENTS.md's checkout policy, no live E2E run beside (the lifecycle leases refuse overlap), subject host signed in; the
   role profiles are recorded (`roles.json`).
3. Start each invocation (`iterate.py`, or `--qualify`) as a visible background task, unbounded unless the owner states limits.
4. At every script stop, act per the directive above; never report "exhausted".
5. After each iteration run `shiploop-run-review advise` and publish; end with one campaign entry and the productivity line (4.7).
6. Never publish exploration commits, change a limit or tolerance, deploy, relabel an unmeasured tolerance as measured, or touch
   another session's runs or branches.

## 4. What would make it more effective (ranked by decisions gained per unit of effort)

1. **Reconcile the backlog before spending a run.** 9 records are with the owner, 6 deferred, and 2 admitted ones are selectable.
   `learning_records.select` ranks by confidence then age, not by expected benefit against cost. ShipLoop has gone from 1.27.0 (the
   calibration build) to 1.36.1; whether each held record is still live is unchecked. Reading them against shipped changes is cheap
   and shows what a run would actually test.
2. **Choose the cheapest instrument that can discriminate, per record** (E25). SPEC: a focused slice or isolated experiment "may
   resolve a narrow mechanism before a full run; it cannot qualify a broader claim". So narrow with the cheap instrument (read the
   upstream records; the real case run to the stage and stopped; a step slice), and qualify only a built candidate. A prediction has
   exactly `case`, `measure`, `direction`, `at_least` (`prediction.validate`): no stage or instrument field. Record the instrument in
   the record's `next_experiment` first; add a field only if that proves insufficient.
3. **Measure the noise on the driver in use.** The only calibration is Terra/high on 1.27.0 and two cases. The default driver is
   Grok 4.6 xhigh, whose spread is unmeasured. `cycle._load_calibration` checks only the scoring digest (not driver, effort or
   ShipLoop version), and already refuses that report on main because the digest covers all of `checks/`. The 27.7% to 35.7%
   false-call figures at 0.25 belong to those two cases on Terra/high; they do not say most current verdicts are wrong. Until a
   driver-matched calibration exists: quality decides first (0 failures in the 16 calibration runs), efficiency stays labelled
   "stated, not measured" (existing), and timing is not evidence under load (the harness marked timing invalid on all 16). Whether
   that calibration is worth its cost is the owner's call (D1, D3).
4. **Give the reviewer a comparator and a coverage record.** The reviewer reads the run, `metrics.json`, the last three commit
   messages plus the latest compared-cycle and ShipLoop source-decision messages (`review.last_commit_messages`) and the records view;
   it gets no matched baseline rows. Matching exists (`run.row_matches`, behind `matching_rows`: host, model, effort, planning mode,
   prompt hash). Because promotion compares arms and the reviewer's efficiency opinions only seed candidates, a comparator improves
   candidate quality, not verdict validity: modest gain, low cost. Separately, `review.validity` checks the process and the review's
   structure, not what was inspected, so the owner's step 3 ("deeply inspect every stage, file and journal") is asked for but never
   recorded. Have the review list the stages and artifacts it read, omitted or could not see, from existing evidence. Record it; do
   not gate on it.
5. **Use advice where the loop stalls, one strong advisor first.** The 9 held and 6 deferred records are where higher reasoning
   fits; the judge routes design challenges out of the loop by design. A four-seat two-pass panel per held record is rejected as the
   default: the single judge already fails validation in about 2 of 9 live judgments (551a951f…), so more seats multiply sessions and
   failure surface with no evidence they judge better. Use Astra at max on a concrete unresolved decision and widen only on
   disagreement. The survey of the advisors skill reports its seats have write tools by default; as evaluators they must run
   read-only (survey report, not re-read here).
6. **Land only what carries acceptance evidence.** A candidate reaches main and a release with the evidence its claim needs: a
   PROMOTE with its prediction confirmed plus the manual live handoff gate, a hand-built qualification, or a narrowly evidenced fix.
   A PROMOTE can leave an `unexplained_gain` (`prediction.outcome`); it does not complete delivery. Exploration commits are
   unevaluated and stay off main (AGENTS.md). Promotion, merge, release and published verification stay separate recorded
   milestones (SPEC). Release and host refresh after preflight and CI are routine (owner, 2026-10-28).
7. **Report productivity per campaign**: accepted, demonstrated generic improvements per total campaign hours and tokens
   (exploration, failed candidates, reviews and verification), with effect size and apparatus learning reported separately. A report
   line, not a gate; promotion counts alone would reward trivial wins.
8. **Hygiene and breadth**: visible background run, no tier beside a live run, a Run Review page per iteration, and contrasting
   cases chosen from the coverage map so ShipLoop is not tuned to one sample.

Not recommended: more gates, more judges, per-attempt panels, or a framework.

## 5. Generic versus ShipLoop-specific

Survey of 13 skills (subagent report; SKILL.md files read, not re-read here): none is a subject-agnostic run, review, judge, improve,
rerun loop with an evaluator boundary. The pieces are spread: `until-loop` (frozen exit checks, trivial-streak counting),
`improve-loop` (a generic campaign, advisors only asked in words not to edit), `rubric-eval` (strong isolation and a statistical A/B
rule; a person drives it), `model-eval` (hidden-test guard), `prompt-research-cycle` (Adopt/Try/Defer commits, anti-flap), `advisors`.
This harness is the only place they meet.

| Generic in substance | ShipLoop-specific |
| --- | --- |
| loop controller: worktree, stop rules, journal, learning commits, branch output | `run.py`: build the plugin, launch `/shiploop` in an empty directory, find the run directory, grade with `checks/`, `cases.json`, fixtures, ports, oracles |
| role profiles and host adapters (`hosts.py`) | `metrics.py` counters (packets, stages, fresh starts, model glue, S-clause rows) |
| the evaluator boundary mechanics | `SPEC.md` S-clauses and the review PREMISE; the candidate paths and release preflight's E2E-round rule |
| the ledger (`learning_records`) and prediction, promotion, spread, epoch | step slices and the stage suite; the Run Review exporter |
| review, independent judge, improver with fail-closed validity | `learning_records.select`'s `target == "shiploop"` |

**Decision: do not generalize or extract now.** The owner scopes work to generic ShipLoop and its generic E2E test, and there is one
consumer. The draft's rule that generic modules must not import ShipLoop names is withdrawn: it would itself begin generalizing, and
today's modules carry ShipLoop assumptions (the PREMISE, `CANDIDATE_PREFIXES`, `select`). Keep the seam conceptual. The trigger to
extract is a real second subject (Backchain, Plan Dispatcher or Improve, all in this repository). The prospective adapter, from
Astra's review and checked against the code's shape:

| Operation | Supplies | ShipLoop today |
| --- | --- | --- |
| `contract()` | mission, obligations, editable paths, withheld inputs, authority | `boundary`, SPEC, the review PREMISE |
| `build(revision)` | a runnable artifact with an immutable identity | `scripts/build-packages.py`, `runner.tree_digest` |
| `run(case, build, profile, instrument)` | execution handle, receipts, resource ownership | `run.py`, `epoch.launch`, `slice.py` |
| `observe(run)` | stage and artifact index, outcomes, costs, explicit unknowns | `metrics.json`, review export |
| `evaluate(run, frozen_contract)` | floors, measures, validity, provenance | `checks/`, `promotion`, scorecard |
| `cleanup(resources)` | ownership-scoped cleanup evidence | `lifecycle.py` |
| `deliver(candidate, acceptance)` | integration and release actions | `scripts/release.py`, `release-push.py` |

## 6. Owner decisions and what stays routine

Owner's call: **go or no-go to build the thin skill now** (bound to an explicit checkout); D1 (tolerance and attempts), D3 (cycle
limits, including whether `NON_PROMOTE_STOP` = 2 stands) and D4 (review sampling) stay open; whether to calibrate on the Grok driver
and whether the scoring digest should cover only the calibrated cases' checks; and every ShipLoop behaviour trade-off among the 9
held records. Routine (the session decides and logs it): authorised investigations, equivalent repairs, release and host refresh
after the required checks. Existing authorisation carries forward without new permission checkpoints.

## 7. Review disposition

Astra (gpt-6-astra, effort max, 2026-11-15) returned "ready with changes". Each claim below was checked against origin/main before use.

| Astra's point | How checked | Disposition |
| --- | --- | --- |
| ledger is 24 records, 76 events: owner 9, deferred 6, admitted 4, open 2, verified 2, refuted 1 | `learning_records.current` | accepted; my tally (last physical line) was wrong |
| one worktree per invocation | `iterate.main` | accepted; draft said per iteration |
| final status `unevaluated` or `comparison_required` | `iterate.main` | accepted; draft said always unevaluated |
| generality case is optional | `cycle.loop`, SPEC "Qualified iteration" | accepted |
| reviewer reads more than three messages | `review.last_commit_messages` | accepted; the missing matched baselines stand |
| a prediction has no stage or instrument field | `prediction.validate` | accepted; draft said it already names the stage |
| bundled harness is 114 files | `git ls-files` | accepted; draft said 61 |
| calibration is Terra/high, 1.27.0, two cases; loader ignores driver | 3423e218…, `cycle._load_calibration` | accepted |
| the two PROMOTEs are not two discoveries | ledger events, 551a951f… | accepted |
| the campaign operator directive is the core duty | SPEC "Campaign operator directive" | accepted; section 3 |
| Claude `env()` does not isolate HOME; withholding is not isolation | `Host.env`, SPEC | accepted; section 1 caveat |
| reorder: backlog, instrument, coverage, advice, delivery; add a productivity denominator | n/a (judgement) | accepted; section 4 |
| no four-seat panel per held record | 551a951f… judge failure rate | accepted |
| "candidates require acceptance evidence", not "only qualify lands code" | `prediction.outcome`, AGENTS.md | accepted |
| keep the seam conceptual; withdraw the import rule; adapter table | code shape | accepted |
| keep the name | repository terms | accepted |

Not relied on: Astra's link to external evaluation guidance (not fetched).

## 8. Unknowns

- Whether max effort improves what the improver applies, and what it costs per iteration (no improver run was launched).
- Wall time and token spread of a cycle on Grok 4.6 xhigh (the only spread was measured on Terra/high).
- Whether the 9 held and 6 deferred records are still live after 1.27.0 to 1.36.1.
- Whether a Claude-host improver's real HOME changes its behaviour in practice, and why the host was left unisolated.
- Whether a multi-model judge would admit better than one Astra judge (three decided records cannot show it).

## 9. Evidence

[docs/experiments/shiploop-e2e-iterate-skill-review-20261115/](experiments/shiploop-e2e-iterate-skill-review-20261115/README.md):
the brief sent to Astra, its verbatim review (`astra-review.json`) and the draft it reviewed (`draft-before-review.md`, which holds
the errors section 7 corrects). Code and records cited by symbol, read at f36332e97f361dab32147f95141324e533dbc12a.
