---
Execute: ask
Status: R0, R1 and the second hello pair done 2026-10-24 (sections 9 and 10); R2 build chosen (the 2.9.0 payload from a pinned checkout, section 10.7); R2 not started; nothing committed
Opened: 2026-10-24
Consumer: the owner, who reads it to approve, strike or re-scope a rung before any run is launched
Source: docs/type1-fast-models-sdlc-journal-2026-10-24.md, section 5 (recommendation 2 and 3)
---

# ShipLoop by-stage effort experiment (E-EFF1): one blocked pair

Question: does lowering reasoning effort on mechanical packets and on Improve passes 2 and later cut tokens and time
without a material loss of quality, in a ShipLoop run? Control against treatment, nothing else varied.

## 0. Read this first

**What the stage data changed since the survey.** The survey recommended "lower effort on mechanical packets". The
stage table says the packets are not where the measured waste sits:

- **No inner-loop stage is mechanical.** `skills/shiploop/scripts/shiploop_stage_spec.py` (`Stage` rows): step-plan,
  test-spec, implement, test, document, verify and carry-forward each author a plan, test, code or document, and verify
  reviews the diff. Only `validate-existing` is script-first and it usually issues no packet.
- **The mechanical stages are the outer ones**: `prepare`, `system-test`, `product-acceptance`, `release-check`,
  `release`, `release-verify`, `operations`. In `test/shiploop_e2e/baselines.jsonl` they are **12.7% of stage seconds** on
  Claude Sonnet 5.5 (28 full runs with current stage names). On Grok 4.7 medium the three rows give 16.8% (the one run
  that reached handoff), 10.0% (blocked at system-test) and 1.2% (a Salesforce case): too few to bound it. That is the
  ceiling of the mechanical arm: the whole 12.7% would have to vanish for a 12.7% saving. (Stage seconds as the harness attributes
  them; LEARNINGS notes it can move time between neighbouring stages. 22 of the 28 Claude rows are `hello`, `battleship`
  and `checkers`.)
- **The Luna finding does not live there.** The 32.5% of wall time spent thinking before a short command (LEARNINGS,
  "Fast planning") is per call inside deliberative stages. Effort is fixed per host session, so a per-stage lever cannot
  reach it. This experiment does not test it (section 8).
- **Improve passes 2 and later are the larger lever**: 118.6 of 647.5 planning minutes (18.3%) on the Luna max run
  (`docs/shiploop-fast-planning-plan-2026-10-04.md`, "Diagnosis"), and Improve was 49% of the first 86 minutes of chess
  run 2 (8 of 21 passes material, 10 no change; LEARNINGS, "Measured (run 2, first 86 minutes)").

So the pair is worth running mainly for its Improve arm. It is still one pair, as asked; the report splits tokens and
time by class so the owner can see which arm paid.

**Decision rule** (owner, 2026-09-27; `skills/rubric-eval/SPEC.md` section 8; memory `eval-decision-priority`): a
material quality difference trumps everything; if quality is near-identical (inside the judge's measured noise) the arm
that significantly uses fewer tokens wins; if tokens tie, less time wins; a tie keeps the control. No threshold is
invented: significance is a 95% cluster bootstrap plus a Wilcoxon signed-rank test over per-scenario means, both agreeing.

## 1. Intent, outcome, self-grade

- **Intent.** Find out whether effort can be set per class of packet and per Improve pass without hurting what the run
  delivers, before anyone puts an effort hint in ShipLoop.
- **Observable end outcome.** One decision record in `docs/experiments/shiploop-effort-by-stage-<date>/decision.json`:
  `winner` (`control`, `treatment` or none), `decided_by` (quality, tokens, time, tie, inconclusive, blocked) and every
  reason, plus the per-class token and second tables, from `rubric-eval analyze` run on the frozen manifest.
- **Self-grade** (the run is not done until all hold): (1) the manifest was frozen and hashed before the first
  decision-round run; (2) both arms ran the same scenarios under one recorded condition (host, model, host build,
  plugin sha, restart positions); (3) every verdict has one judge; (4) every blocking check is listed with its value;
  (5) the journal entry exists in the same commit as the record; (6) no ShipLoop skill file changed.

## 2. Grounding: what exists and what is missing

| Need | Exists | Gap |
| --- | --- | --- |
| A stage boundary the harness can see | `test/shiploop_e2e/clear.py`: positions fire from run state (works on every host at a boundary); `slice.py` `--clear-at` | `run.py` has no `--clear-at`; full runs need the same polling stop |
| End a session and start the next with a different effort | `slice.py` main loop: continue with `host.argv(..., resume=session_id)`; `run.py` `resume_identity` (an explicit `--effort` wins on resume); effort flags: Grok `--reasoning-effort`, Claude `--effort`, Codex `-c model_reasoning_effort` (`hosts.py` `argv`) | nothing ends a session on a class change; whether a resumed session honours a new effort is untested |
| Which stage is running | state.md stage name; `Stage` table in `shiploop_stage_spec.py` | the class list (section 3) is not in code |
| Which Improve pass is next | `metrics.improve_reviews` counts `review-<n>.md` per child under `.shiploop-improve/` | no "pass 2 is about to start" position; U7 |
| Tokens and seconds per class | `metrics.per_stage`, session usage rows (`output_tokens`, `reasoning_tokens` on Grok usage events) | per-class attribution; whether Claude reports thinking tokens separately (U2) |
| Quality, script-scored | slice/run verdicts, `seeded_defects.py`, `arms.py` hard gates (refusals, warm `next` calls, SPEC flips, ledger obligations, redone work) | `redone` is empty on Grok and Codex (`clear.py`), so that gate is unmeasured there |
| Quality, judged | `skills/rubric-eval` (Opus 5.5 medium, 3 passes, noise measured on the round's own outputs) | no suite grades run artifacts; the judge needs acceptance on the new output type |
| A decision | `rubric-eval analyze` (section 8 rule); `arms.py` | `arms.py` decides on bytes ingested, which an effort change does not move; it is used for its hard gates only |
| Hermetic harness tests | `test/shiploop-e2e-slice.test.py`: `SliceCase` writes a scripted `fake_host.py`; `ClearTriggerTests` and `ClearProbeTests` are the pattern for boundary triggers | cases for the effort schedule |

## 3. Design

**Arms.** Both run every session through the same restart schedule. Control keeps one effort everywhere. Treatment
lowers it on classes M and I2 and keeps the control effort on class D.

| Class | Definition (frozen before any run) | Control | Treatment |
| --- | --- | --- | --- |
| M | the stages `prepare`, `system-test`, `product-acceptance`, `release-check`, `release`, `release-verify`, `operations`: the model runs, checks and reports; it writes no product file and no plan | host default | `low` |
| I2 | an Improve child's pass n >= 2 in any stage | host default | `low` |
| D | every other packet, Improve pass 1, and `handoff` (it authors the final document) | host default | host default |

Reason for the exclusions: Improve pass 1 found a real defect in 9 of 12 first-pass changes while passes 2 and 3
changed nothing in any of the 12 (LEARNINGS, "Most first-pass findings were real"); the spec, plan and test packets are
the deliberative ones the arXiv 2607.02436 result (High to xHigh, 28% to 89% first-try perfect) argues against touching.

**Blocked, and why restarts are in both arms.** Changing effort needs a new host session at a class boundary. A restart
is itself a treatment (cost of re-sending context, a cold cache), so the control restarts at exactly the same positions
and changes nothing at them. The only difference between arms is the effort flag of the sessions that run M and I2.
The next session continues the same transcript (`resume=session_id`), so context is not cleared and `no_redo` is not at
stake. If a host ignores a changed effort on resume (probe P2), the fallback is a fresh session at the same positions in
both arms, as `clear.py` already does (S-6 clear probe).

**Scenarios and trials.** `rubric-eval` blocks any win with fewer than 8 scenarios. The eight non-platform cases in
`test/shiploop_e2e/cases.json`, chosen before any result and by cost only (R0.2 prints each case's control seconds from
`baselines.jsonl`): `hello`, `seat-reservations`, `battleship-scoring`, `csv-report`, `unit-converter`, `word-report`,
`temperature-report`, `temperature-plain`. `battleship` and `checkers` are left out as the longest, and the Salesforce
cases need the owner's org. One trial per arm per scenario: 16 full runs. Arms alternate order per scenario by a
seeded draw recorded in the manifest, so drift in API load is spread over both.

**Host, model, judge.**
- Decision subject: **Grok 4.7 at medium** (control) against **Grok 4.7 at low** on M and I2 (owner default subject, SPEC
  section 6). If Grok credits are out at R0, the decision subject is Codex `gpt-6-luna` at xhigh against low, after the
  same probes; Sonnet is exploratory only (SPEC section 6) and is used for the shakedown, never for the decision.
- Judge: **Opus 5.5 at medium**, one judge for the whole round, three grading passes, noise measured on the round's own
  outputs and divided by the square root of the pass count. Never Haiku.
- Adversarial review of this plan and the harness change before R2: gpt-6.1-sol at medium (memory
  `luna-unreliable-use-sol`), a family other than the proposer's.

**Quality instruments.**
- Q1, script-scored, hard gates (an arm that trips one cannot win): the run's verdicts and case checks; first-pass
  refusals paired against control (restart-induced ones set apart: section 10.1); SPEC clauses flipped; ledger obligations lost; an Improve pass whose `trivial` claim
  disagrees with the script's tree digest; `redone` where measurable (Claude only).
- Q2, judged: the prose that M and I2 packets produce, which is what a lower effort could degrade without a script
  noticing: `system-test`, `release-verify` and `operations` reports, `product-acceptance` evidence, and Improve
  `review-<n>.md` for n >= 2. A new `rubric-eval` suite `shiploop-run` (R0.5) grades each against criteria stated before
  and after the text: states only facts the run recorded (quote-checked against state.md or the ledger), required fields
  present, evidence dated after the last edit, no unsupported claim. Percent of rubric points per artifact, mean per scenario.

**Tokens and time.** Tokens: prompt plus output, reasoning included, as each CLI reports them, summed over a run's
sessions; an output with no usage is left out, never counted as zero. Time: host session seconds summed over the run.
Both reported per class (M, I2, D) from the same runs, descriptively; the decision uses the run totals.

**Not in this pair: escalation.** An earlier summary mentioned rerunning a refused or changed-tree low-effort pass at the
default effort. That is a third factor, so it is out. The harness records the events that would trigger it (a refusal on
an M packet; a tree change at an I2 pass) so a later design can price it.

## 4. Rungs

**R0. No model calls except the two probes. Cost: minutes.**
- R0.1 Work: add `test/shiploop_e2e/effort.py` (class of the current position from state.md and the review count;
  schedule file `{M: level, I2: level, D: level}`), wire it into `slice.py` and `run.py` as `--effort-schedule FILE`
  beside `--clear-at`; control and treatment use one code path and differ only in the file. Scripted-fake-host cases for:
  boundary found, restart positions identical across the two schedules, effort recorded per session in `sessions.jsonl`,
  an unknown class refused. Exit: those cases pass with the touched suites only (memory `test-economy-policy-2026-10-17`),
  `python3 -B` once after the last edit.
- R0.2 Work: print, from `baselines.jsonl` and the local run folders, per candidate case the control seconds, the Improve
  passes per child and how many are pass >= 2, and the M share. Exit: the table is in the journal; the eight scenarios
  and the Improve mass per host are frozen in the manifest with the reason for each. Resolves U3 and U4.
- R0.3 Probe P1: one tiny call per decision host with the treatment level; the invocation record shows the effort used and
  the usage shows fewer reasoning tokens than at the control level on an identical prompt. Exit: both recorded. Resolves U1.
- R0.4 Probe P2: resume a one-call session with a changed effort; usage shows the change took effect. Exit: recorded; if
  not, the fresh-session fallback is the design. Resolves U1.
- R0.5 Work: author the `shiploop-run` suite and run the section 7 acceptance check (re-grade 30 artifacts,
  linear-weighted kappa above 0.60 on the Landis and Koch bands, noise reported). Exit: `references/judges.json` holds
  the figures; below the band the criteria are revised and the check repeated. No decision round runs before this.
- R0.6 Work: `seeded_defects.py verify` and the existing slice suites still pass (the harness change touches shared code).
- R0.7 Work: freeze `manifest.json` (scenarios, order draw, class list, schedules, plugin sha, host builds, analysis
  command) and write its hash into the journal. Exit: the hash is committed before R2 starts.

**R1. Shakedown, exploratory, Claude Sonnet 5.5, `hello` and one heavier case, both arms explicit at `medium` and `low`.**
Not evidence for the decision. Exit: restarts fired at identical positions in both arms; each session's effort is the
scheduled one; tokens and seconds attribute to M, I2 and D; the Improve pass 2 boundary was found from state, not from
the model's report; the judge graded the artifacts; the analysis command ran end to end on the two runs.

**R2. The pair. Grok 4.7 (or Luna xhigh), 8 scenarios x 2 arms, one trial.**
Launch each run with `run_in_background` and `--resume-run` after the background limit (about 2 hours), never nohup
(memory `detach-long-runs`); arm A and arm B of one scenario are adjacent in the queue, at most two runs at a time
(load average hit 34.5 on 18 CPUs on 2026-10-17); a progress monitor re-armed every 30 minutes. No engine change and
no restart of a run mid-batch (memory `batch-run-to-completion`). Exit: all 16 runs reached a terminal state, or an
unfinished run is a recorded outcome of its arm and not dropped; evidence exported compactly to
`docs/experiments/shiploop-effort-by-stage-<date>/`; judge passes 1 to 3 graded; `decision.json` written by
`rubric-eval analyze`.

**R3. Only if R2 favours treatment. Fresh confirmation.** A fresh run on the frozen text with new draws, on the second
host (Luna xhigh against low, or Grok), plus a replay of every control I2 pass that changed the tree, at low effort, to
test whether the same finding is reproduced (the sensitivity R2 cannot give; U6). Revising and retesting until something
clears is a search, so the result that counts is the confirmation (SPEC section 8).

## 5. Outcomes

| Result of R2 | Meaning | Next |
| --- | --- | --- |
| Treatment wins on tokens or time with quality near-identical and no block | effort can be set per class | R3, then a build plan for a script-derived `effort_class` line in the packet and a driver that applies it (`shiploop-drive`) |
| Quality worse, or a block (gate, guardrail, overbuilt, judge) | per-class low effort costs quality for these classes | record the failing class from the per-class tables; a narrower second pair (I2 only, or M only) is a new plan, not an automatic rerun |
| Tie at every level | no reason to change | keep control; close the lever |
| Inconclusive | too few scenarios or too much spread | add scenarios or trials as SPEC section 8 says; state which in the journal |

## 6. Impact on other spec items

- **SPEC S-6 (context may be cleared between stages)**: restarts that continue the transcript do not exercise S-6; the
  fresh-session fallback does, and its `no_redo` verdict stays unmeasured on Grok and Codex (`clear.py`).
- **SPEC S-14 (unattended)**: restarts are harness-driven; no packet or hook asks a person anything.
- **Harness boundary**: ShipLoop launches no model, and nothing here changes a skill file, so no `changes/` note,
  release, marketplace refresh or `Skill-Craft-Release` commit is involved. The harness files that change are under
  `test/shiploop_e2e/`; any push of them follows `quick --changed-from <base>` (memory `quick-needs-changed-from`).
- **Test economy**: R0 runs only the touched suites once after the last edit; no local full tier.
- **Environment control**: Claude runs keep `--strict-mcp-config` (LEARNINGS, "Claude connector isolation"); Grok runs
  use the isolated HOME; both arms use the same plugin sha, host build and fixture commit.

## 7. Unknowns, each with its resolution (outcomes: section 9)

| # | Unknown | Resolved by |
| --- | --- | --- |
| U1 | Does Grok accept `low`, record it, and honour a changed effort on `--resume`? Same for Claude and Codex | P1 and P2 (R0.3, R0.4) |
| U2 | Does each host report reasoning tokens per call? Grok usage events carry `reasoning_tokens`; Claude is not confirmed | read one `events.jsonl` per host in R0.2; a host without it uses total output tokens and says so |
| U3 | How much Improve pass >= 2 mass exists per host? Sonnet showed at most 3 passes in any child, so Claude may have little | R0.2 count from run folders; if Grok shows little too, the I2 arm is reported as under-powered, not as a null |
| U4 | Cost of 16 Grok full runs | R0.2 estimate shown to the owner before R2; fallback below |
| U5 | Does the judge grade run artifacts reliably? | R0.5 acceptance check |
| U6 | R2 may contain no event at stake (control pass >= 2 never changes the tree), so it cannot show a loss of that kind | R3 replay of saved control passes |
| U7 | Exact moment pass 2 begins (note written vs next packet issued) | read the Until Loop runtime state; use its counter, not a file count |
| U8 | Claude's default effort is unrecorded (`effort: null` in baselines) | the shakedown names both levels explicitly; no Claude row is compared with an old baseline |

**Budget fallback.** If U4 is too high, run four scenarios first. `rubric-eval` lets a harm block on the interval alone
and needs both tests plus eight scenarios for a win, so four can stop the idea but cannot approve it; the other four
are then added as the SPEC's "add scenarios" route, with the same frozen manifest.

## 8. Not in this plan

- Per-call effort inside a stage (the Luna 32.5% finding): not settable in a session; a different lever, if any.
- A Type 1 model tier, Haiku, or any specialised fast model (journal section 5, recommendation 1).
- Escalation on refusal or tree change (section 3).
- Changing any packet, skill file, hook, or the `shiploop-drive` driver.
- Luna as a second decision host before R3.

## 9. R0 results (2026-10-24)

R0.1 to R0.7 are done; R1 and R2 have not started and no decision-round run exists. Evidence is in
`docs/experiments/shiploop-effort-by-stage-20261024/`; the journal entry is `docs/type1-fast-models-sdlc-journal-2026-10-24.md`
section 8. The frozen manifest is `manifest.json` there, and `freeze_manifest.py --check` says what changed since.

**What was built.** `test/shiploop_e2e/effort.py` and `--effort-schedule` on `run.py` and `slice.py` (restart at every class
change, control and treatment on one code path, restarts outside the resume budget, the effort of each session in
`sessions.jsonl`, host level validation because Claude ignores an invalid `--effort`); tests in
`test/shiploop-e2e-slice.test.py` (12 pure, 1 fake-host) and `test/shiploop-e2e.test.py` (4 through `run.main`); the
`shiploop-run` rubric-eval suite with `import_run.py`; `run_totals.py` and `freeze_manifest.py` in the experiment folder.

**Unknowns.**

| # | Outcome |
| --- | --- |
| U1 | Resolved. Grok accepts `xhigh, high, medium, low`; `low` gave about 30% fewer reasoning and output tokens than medium on means (individual runs overlap). A resumed session honours a changed effort (resumed low at 0.63 to 0.79 of resumed medium, the fresh pair's ratio 0.69 to 0.71); resumed runs carry a token offset in both arms. The fresh-session fallback is not needed on Grok. Claude cannot resume in this harness |
| U2 | Resolved. Grok `usage` events carry `output_tokens` (reasoning included), `reasoning_tokens`, `input_tokens` and cache fields. Claude reports `usage.output_tokens_details.thinking_tokens`, noisy at low effort; `output_tokens` is its primary measure |
| U3 | Resolved. Grok: 134 of 226 recorded Improve passes are at pass 2 or later; Claude: 273 of 655 (most children stop at one pass). Of the 100 Grok passes >= 2 that recorded whether the tree changed, 23 did |
| U4 | Open, see below. The estimate is 8.9 h for 16 runs at two at a time (17.8 h serial) at a 5.3x Grok/Claude ratio, 16.7 h at 10x; four scenarios have no Claude timing |
| U5 | Resolved with a limit. Opus 5.5 medium on `shiploop-run`: kappa 0.914 (almost perfect), noise 1.67 points, 30 artifacts graded twice. Improve reviews scored 100 in both gradings, so the judge may not separate a weaker low-effort review; Q1 gates and the R3 replay carry I2 quality |
| U6 | Narrowed. R2 will contain events at stake on Grok (23 of 100 recorded pass >= 2 changed the tree); the R3 replay stays |
| U7 | Resolved by code. The Until Loop runtime writes the latest packet to the child's receipt path atomically before printing it (`_write_receipt`); `effort.running_pass` reads `status` and `progress.action_number`. First check against a live run is R1 |
| U8 | Unchanged. Claude rows record `effort: null`; the shakedown names levels |

**Decisions made in R0.**
- Tokens are prompt plus output as the CLI reports them (prompt = `input_tokens` + cache read + cache creation; output includes
  reasoning), summed per run; seconds are the sum of host session spans. Output alone and reasoning are reported beside them.
  Every imported artifact carries its run's totals, so a scenario's mean is the run's (`run_totals.py`, `place --tokens`).
- The mechanical share on Grok is 16.8% (one complete run), 10.0% (blocked at system-test) and 1.2% (a Salesforce case): it is
  not bounded; the 12.7% on Claude stands.

**Limits recorded.** Arms pair by order within case and slot, so a pass present in one arm only is dropped from the quality
comparison (its cost stays in the totals). The acceptance set mixed Grok and Claude artifacts. Opus judge tokens and seconds
are not recorded by rubric-eval (the agent's tally: 123 calls, about 1.23M tokens).

**Cost, still an estimate.** Grok per-run time is uncertain by about 3x: 5,599 s for a finished 1.22.0 battleship run, and at
least 14,229 s of sessions (912 model calls, 115.5M prompt tokens, 0.84M output tokens) for a 2.6.0 battleship run the owner
stopped at 232 minutes. Neither is a 2.8.0 run. Grok dollars are not metered (CLI-reported scale: about $143 for 16 runs at
the low estimate). **Recommended before R2:** R1 as one `hello` pair on Grok 4.7 (control and treatment), about two hours at
two at a time, which times Grok under 2.8.0, runs the schedule against real Improve packets (U7), and runs the import and judge
pipeline end to end; optionally a Claude timing run of the six scenarios that lack one (about $25).

**Release note.** Committing `skills/rubric-eval` needs a `changes/rubric-eval/<slug>.md` note or a `No-Change-Note` trailer.

## 10. Revisions after R1 (2026-10-24)

R1 ran one `hello` pair on Grok 4.7 (control and treatment, two at a time; journal section 10). The machinery worked: every
restart into the Improve pass-2 class matched a child that really reached pass 2 (3 of 3), and mechanical-stage boundaries fell at
the same stages in both arms. It also showed three things the design did not handle. The manifest is re-frozen as revision 2
(`manifest.json` records `supersedes_sha256`; no R2 run existed). Classes, schedules, scenarios, judge and the decision rule are
unchanged.

**10.1 Restart-induced refusals: avoid what can be avoided, attribute the rest.**
- *Finding.* Every Improve pass-2 cycle produced two `improve-pass` refusals in the sessions the harness started for its boundaries:
  one right after the restart into pass 2 (the review submitted before it was written) and one after the restart at loop
  completion (the loop re-run after it ended). 3 cycles, 3 pairs (control 4 refusals, treatment 2). A Grok run with no restarts
  (`2026-10-18/battleship-1`, 17 children) had none of the first and one of the second. The 3 mechanical-stage boundary pairs
  produced none. The refusal count is a gate (section 3, Q1) and the number of cycles differs by arm.
- *Avoided.* (i) The I2 class is held while the loop is closing: a packet that is `complete` or `stopped` while the child is still
  bound is indeterminate, so no boundary falls between the loop's completion and the model's own `complete` call; the I2 to D
  boundary then falls after that call, like the mechanical ones (`effort.running_pass`). (ii) The session after a boundary is
  told that its earlier commands took effect and not to repeat one (`effort.RESTART_NOTE`, the `note` of the resume prompt; both
  arms). Tested on a live run in the second pair (section 10.5): the hold works, the note does not.
- *Attributed.* `run_totals.py refusals` counts navigator refusals once each (the stream repeats a result) and sets apart the two
  `improve-pass` refusals above when they fall in a session started for a boundary. The refusal gate counts the rest; both counts
  are reported for each arm. On R1: control 10 refusals (4 set apart, 6 other), treatment 5 (2 apart, 3 other). A real
  `improve-pass` error inside such a session would be hidden, the same way in both arms.

**10.2 Measures beside the run totals.**
- *Finding.* In R1 the M class was 17.3% of session seconds and 15.3% of output tokens in control, I2 5.0% and 5.3%, D 77.7% and
  79.4%. Within the M sessions low effort used about 40% fewer reasoning tokens per call (151 against 252), 19% fewer output tokens
  per call, 41 calls against 55, and 420 s against 751 s. In D, medium in both arms, reasoning per call differed by +24% and
  seconds by +18%. The unchanged class varied several times more than the M effect, so run totals at one run per arm cannot show
  it. The I2 sample was one pass of 7 calls.
- *Added.* Beside the totals, with the same tests (95% cluster bootstrap and Wilcoxon over per-scenario means): tokens and
  seconds of the M-class sessions per scenario (every run visits the same mechanical stages, so the measure is matched by stage
  type), and of the I2-class sessions per scenario where a run reached pass 2 (a run with none is left out, never zero).
  Descriptive only: reasoning and output tokens per call by class. Built by `run_totals.py classes` and `tokens --class M|I2`,
  placed into their own imported run folders.
- *Reading rule.* The run totals decide, as the decision rule says. A class measure does not decide. If the totals are
  inconclusive and quality is near-identical, a significant saving in the M class is reported as "mechanism seen, total not
  detectable at 8 scenarios", and the owner decides whether more scenarios are worth their cost.
- *Power, stated.* The M class is about 15% of tokens; a 40% cut in its reasoning is a few percent of a run, and the unchanged
  class moved by tens of percent between two R1 runs. Expect the totals to be inconclusive at 8 scenarios unless variance is lower
  than R1 suggests; the class measures are what can resolve it.

**10.3 Time and cost restated** (`cost/e-r2-time-restated.json`; estimates from one case).
`hello` took 4,340 s and 4,504 s in R1 and 3,986 s and 4,063 s in the second pair (session time; mean 4223 s), against the
earlier estimate of 2,558 s (factor 1.651). Updated after the second pair (section 10.5).

| Case | Hours for 16 runs, serial | At two at a time | Assumption |
| --- | --- | --- | --- |
| Low | 18.7 | 9.4 | `hello` measured; the seven others as estimated before R1 |
| Central | 29.4 | 14.7 | `hello` measured (four runs); the others at the earlier estimate times 1.651 |
| High | 57.7 | 28.8 | `hello` measured; each other case as long as the 2.6.0 battleship run stopped at 232 min (14,229 s, a lower bound) |

CLI-reported cost (a lower bound, not a bill; Grok dollars are not metered): R1's two runs $4.08, about $0.00046 per session
second, so about $49 for 16 runs at the central estimate, against $143 at the older rate. Judging (about 480 grades) is extra and
unmetered. The Grok account is shared: another session's batch runs three concurrent slices for 3 to 9 hours, and seconds are a
measured quantity, so R2 needs a window with no other Grok load (the owner or that session to decide).

**10.4 R1 status against its exit (section 4).** Restarts fired at identical class positions where the trajectories matched, each
session ran at its scheduled effort, tokens and seconds attribute to M, I2 and D, the Improve pass-2 boundary was found from the
runtime packet, and the import pipeline ran on real output. Not done: the judge on the R1 artifacts (no judge calls were made)
and a Claude run.

**10.5 The second hello pair (journal sections 13 and 14).** Run on this checkout's 2.8.0 build (`--source checkout`): the marketplace had
moved to 2.9.0, which changes the Improve route, and its source is gated on local HEAD == origin/main. Another session's Grok run was
active, so the seconds are not comparable with R1's.
- *A defect, found and fixed.* Grok reports its session id only when a turn ends. The first control run's first boundary came 8 minutes
  into its first turn; the host was killed with no id to resume from and the run ended at spec. The first fix (end no session before an
  id exists) removed the kill but broke the design: control's first turn lasted almost the whole run (9,665 event lines before any id),
  so control had 1 restart against treatment's 9. The final fix: the harness chooses the first Grok session's id (`--session-id`,
  `planned-session-id.txt`) and resumes by it from the first second; the guard stays for hosts without the flag. Probe
  (`probes/session-id-midturn-kill.json`): a session started with a chosen id, killed at 14 s mid-turn, was resumed and recalled what it
  had written and the command it was running.
- *The refusal fixes, live (treatment: 9 restarts, 2 pass-2 cycles).* "Loop already ended": 0 (R1: 3 of 3 cycles), so the hold works.
  "Write this pass's review": 2 of 2 cycles (R1: 3 of 3), so the restart note has no measurable effect. Control, which had no
  restarts, had 0 of that kind in its 2 pass-2 cycles, which shows the remaining one is restart-induced. It stays, attributed by
  rule (10.1): one refused call per D to I2 boundary.
- *The totals still do not separate the arms.* Seconds 3,986 (control) and 4,063 (treatment); output tokens 210.6k and 221.6k; reasoning
  tokens 103.7k and 99.6k. Class D, medium in both, differed by -10% in reasoning per call between the arms here and +24% in the
  other direction in R1. In the M class, low used 193 reasoning tokens per call against 208 at medium (-7%; R1 -40%), over 14
  control calls. Per-run noise of 10 to 25% in the class low effort does not touch is the finding.
- *Pair 2's control is a no-restart reference, not the blocked control.* The blocked control (restarts at the same positions as
  treatment) was R1's. With the chosen-id fix the symmetric design is restored but has not been run since.
- *Unsettled.* The plugin pin: the marketplace serves 2.9.0 and the manifest named 2.8.0, so R2 needs either the marketplace build
  after the local checkout is synchronised, or a pinned checkout build; this is the owner's call.

**10.6 R2 on the marketplace 2.9.0 build (journal section 15).** The owner chose the marketplace build. What that takes:
- *The gate is not about the local HEAD.* `version_gate` (run.py) refuses unpublished local commits, a version that differs from the
  catalog, unreleased change notes on origin/main, and a failed CI. A HEAD behind origin/main is allowed (the comment at the top of
  run.py that says "local HEAD == origin/main" is out of date). It refuses today: origin/main has 3 unreleased change notes
  (`dependency-directories-from-cards`, `not-run-refusal-exit-code`, `unread-refusal-points-at-card`) while the marketplace still
  serves skill-craft 2.9.0 / ShipLoop 1.9.0. A marketplace launch needs `scripts/release.py` to run and push; that release moves the
  marketplace past 2.9.0, so "marketplace 2.9.0" holds only while the gate passes at 2.9.0. The fallback is `--source checkout` from the
  pinned harness worktree, which builds the same 2.9.0 source with no gate and no drift (needs the owner's OK).
- *Why the harness checkout still matters.* The harness imports ShipLoop's modules (navigator, stage table, standalone Improve, store)
  from its own checkout, and `effort.running_pass` reads a child's receipt packet through them; they must match the plugin under test.
  At 2.9.0 the names that detection uses are unchanged against 2.8.0 (`receipt_path`, `packet.json`, `progress.action_number`,
  `active_improve`).
- *The sync, and what it took.* A plain fast-forward of the canonical checkout is refused by git because upstream touched one of the
  seven files with uncommitted edits (`test/shiploop-e2e.test.py`); the other six and every untracked file do not overlap upstream. The
  patch of the seven files applies cleanly with `git apply --3way` on origin/main and on the 2.9.0 release commit. Another session
  rebased the canonical checkout onto origin/main meanwhile (autostash; all uncommitted work verified intact), and 13 more harness
  commits changing `run.py` and `cases.json` are due. So the experiment runs from a pinned worktree at the release commit
  (`sync/make_r2_harness.sh`, built from copies kept in `sync/`), with the changes uncommitted; the canonical checkout is not touched.
- *Verified in the pinned worktree:* the effort tests (20 and 5), `shiploop-e2e-slice` (78 tests) and `shiploop-e2e` (442), all pass;
  on the origin/main tip with the same overlay they also pass.
- *Launch guard* (manifest `plugin.launch_guard`): before every run, `run.py --preflight-only --host grok` must end OK and name 2.9.0 /
  1.9.0, or the queue stops; a release in the middle of the batch would put the arms on two engines.

**10.7 Decision: R2 runs on `--source checkout` from the pinned worktree (owner, 2026-10-25).** The marketplace gate was refusing
(10.6), so R2 does not use it. The runs use `--source checkout --plugin-dir <worktree>/plugins/skill-craft`, the committed payload of
the 2.9.0 release commit (31933a73): `plugins/skill-craft` is identical between that commit and origin/main, and the marketplace
serves origin/main's `plugins/skill-craft` byte for byte, so the plugin under test is the 2.9.0 marketplace payload (skill-craft
2.9.0 / ShipLoop 1.9.0, digest 86b138e1652e) with no gate and no drift. The default checkout build was not used because it also packs
the experiment's rubric-eval overlay: three paths under `skills/rubric-eval`, digest 4dd13076c669 (`sync/plugin-build-comparison.json`).
The launch guard changes to: the harness worktree is at 31933a73, `freeze_manifest.py --check` is clean, and each run's
`invocation.json` `versions.plugin_sha256` equals the payload digest; a run on any other build is not an R2 run. The 10.3 time
estimate and the Grok-window requirement are unchanged.
