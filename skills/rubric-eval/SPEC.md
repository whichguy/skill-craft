# rubric-eval specification

The reference for how prompt changes are evaluated in this repository. Check it
before running an experiment; change it when the process changes. The
architecture-rubric results that shaped it are in
`docs/shiploop-architecture-rubric-results-2026-09-26.md`.

## 1. Purpose

Decide, with evidence, whether a change to a prompt (a packet block, a review
focus, a platform card, a judge) makes a model's output better against a rubric,
without regressing what the rubric guards. It answers one question per
experiment: does arm B beat arm A on the same scenarios, under the same
condition, by more than the noise?

It does not replace `compare-prompts` (a quick pairwise check of two prompts on
a folder of inputs) or `adversarial-review` (which finds what an experiment
should test). It composes with both.

## 2. Composable parts

Each step is a separate command with a file contract, so any step can be run,
rerun or replaced on its own, and other skills can call it.

| Step | Command | Reads | Writes |
| --- | --- | --- | --- |
| Model call | `call --model sonnet\|grok` | prompt on stdin | text on stdout |
| Exact text | `extract SOURCE [--symbol NAME]` | a source file | the text, and its hash on stderr |
| Build | `build RUN --arm NAME=PATH[::SYMBOL] ...` | a suite, arm texts | `RUN/prompts/*.txt`, `RUN/manifest.json` |
| Run | `run RUN --model M` | prompts | `RUN/out/*.json`, `RUN/stubs.log` |
| Judge | `judge RUN` | outputs | `RUN/judge/*.json`, `RUN/judge/failures.log` |
| Analyze | `analyze RUN --baseline ARM` | verdicts | `RUN/analysis.json` |
| Reliability | `reliability RUN --n 30` | verdicts | `RUN/judge_regrade/*.json`, a summary |

Names: an output or verdict file is `<scenario>_<runtime>_<arm>_<trial>`; arm
names contain no underscore.

## 3. Suites

A suite is a folder: `rubric.json` (criteria, grade `anchors`, composite
`groups`, `guardrails`), `scenarios.json` (scenarios with `request`, `tier`,
`runtimes`, optional `runtimes_ext` and `ui`, `applies`, optional `applies_ui`,
`overbuild`; plus `tiers`, `runtimes` descriptions and `runtime_names`), and
`frames/*.txt` (templates with `{request}`, `{environment}`, `{arm}` and, for
review frames, `{plan}`). Frames are filled by token replacement, never
`str.format`. Any frame containing `{plan}` is a review frame, whatever its
name: it needs `--plans-from` and `--plans-arm`, and only the output's
`## Revised plan` section is graded. The first suite is `suites/architecture`,
with frames `plan`, `review` (adds a scope guard) and `review-bare` (none, so
the review focus under test must carry its own guard).

A new scenario needs a request in a user's words, an expected tier, its
applicable criteria and an overbuild note. Include scenarios on both sides of
any new pressure, so overbuilding and underbuilding are both visible.

## 4. Arms

An arm's text comes from the source it would ship in, by exact extraction
(`extract`), never retyped. The manifest records each arm's source and hash. A
candidate that will ship must be tested as the text that ships; if the shipped
text differs from the tested text in any way, say how in the results.

## 5. Condition invariants

Every arm in a comparison runs under one condition. Break any of these and the
comparison is void. `run` records the model and tool setting in the manifest
and refuses to mix conditions in one run folder; `analyze` refuses to ship a
comparison whose manifest records none. A baseline that is an input rather
than a run this round (the unreviewed plans of a review experiment) is marked
`"role": "input"`.

- the same frame, scenarios, runtimes, trials, subject model, tool setting and
  judge;
- the baseline rerun in the same round, not reused from another condition;
- no MCP servers or plugins in any headless call (`call` enforces this);
- a control cannot read the treatment (no shared readable directory);
- stubs (graded text under 150 words) rerun with the same prompt up to three
  times, then excluded and logged, never graded as failures;
- a prompt that asks the model to check something (a review focus that says to
  run a command) runs with `--tools Read` from an empty directory; with no tools
  a model may announce a tool call and stop, which is a stub, not a result;
- the judge sees one output at a time, never the arm name;
- one judge for the whole round: every verdict records `judge_model`, and
  `analyze` refuses to decide when a run's verdicts come from more than one
  judge (a changed default once let running loops write Grok verdicts into a
  Sonnet-graded round, invisibly).

## 6. Models

- **Subject (execution): `grok`** (grok-4.7, medium effort), ShipLoop's real
  host. `sonnet` is allowed for exploratory rounds; name the subject in every
  result, and never assume a result on one subject holds on another.
- **Judge: `opus`** (claude-opus-5-5, medium effort), exactly one per round,
  never two. It is a different model family from the Grok subject, so it cannot
  favour its own family's phrasing. A round keeps the judge it started with;
  switching mid-round makes its arms incomparable. A new judge must pass the
  section 7 acceptance check before its first decision-making round.
- **Ship decisions** rest on a fresh confirmation run with Grok as subject and
  Opus as judge.
- **Adversarial reviewer**: a model family other than the one that proposed the
  change (see the `adversarial-review` skill).
- Never Haiku.
- History: architecture rounds 1–5 used Sonnet as subject and judge; they are
  exploratory evidence for choosing what to confirm.

## 7. Judge

Evidence first: for each applicable criterion, quote the shortest exact span of
the plan that decides it, then grade from that quote (`met`, `partial`,
`missed`, `overbuilt`, `na`), with grade anchors in the prompt and the criteria
stated before and after the plan. Each call times out, retries up to three
times and logs a final failure. A new judge version must be re-graded on at
least 30 plans before use; accept it if the mean per-plan score change is 0.03
or less (judge v2: 0.017; v1: 0.041) and the ship decisions of the last
completed comparison do not change under it.

Known weakness (adversarial review of this skill, F4): only 77% of judge v2's
quotes are exact substrings of the plan (89% after normalising whitespace and
markdown); most misses are quotes shortened with "...". Judge v3 will forbid
ellipses, verify each quote fragment against the plan, and downgrade a met or
partial grade whose quote is not found. It must pass the acceptance check
above before use. The judge is shown the expected tier and overbuild note by
design, because proportion cannot be graded without them.

## 8. Statistics and the ship rule

Scores: met 1, partial 0.5, missed and overbuilt 0, averaged over graded
criteria. Compare arms **paired** on the same scenario-runtime-trial cells:
mean difference, a 95% bootstrap interval (4,000 resamples), and cells won and
lost. Report composites for every group in the suite.

Intervals resample whole scenarios by default (`--cluster scenario`), so
repeated trials and runtimes of one scenario are not counted as independent.
Under shuffled labels (no true effect) on round-3 data, this rule falsely
shipped 3.3% of the time (cell resampling: 2.5%).

A change **ships** only when all of these hold:
1. the overall 95% interval against the baseline lies above zero, over at least
   8 scenarios;
2. every guardrail group (`guardrails` in the rubric; for architecture:
   proportion and safeguards) has a comparison, its mean is not below −0.02,
   and its interval is not wholly below zero;
3. overbuilt-scope grades and platform errors do not rise by more than a
   quarter of the baseline's count (at least 2), and stub and `na` rates differ
   by no more than 5 points between arms;
4. the run's manifest records one condition (model, tools) for every arm run
   this round, and only the baseline may be an input from an earlier round;
5. the adversarial-review loop (section 9) is complete;
6. a **fresh** confirmation run on the text as it will ship passes rules 1–4.
   Revising and retesting until something clears is a search, so the result
   that ships is the fresh confirmation, never the run that selected it.

`analyze` applies rules 1–4 and reports them, with every failing reason, as
`decision`.

## 9. Change lifecycle

The lifecycle applies to any change a suite can measure. A change needs a
suite whose criteria measure what the change affects; if none exists, build one
first, or record why the change is not evaluated this way. Grading a platform
card, a judge or a non-architecture packet block against the architecture suite
alone is not evidence about it.

1. **Hypothesis**: what the change should improve, and what it might harm.
2. **Experiment**: arms extracted from source; build, run, judge, analyze.
3. **Adversarial review** of the proposed change and its evidence
   (`adversarial-review review`), by a different model family. An empty
   findings list completes this step only with the reviewer's output recorded.
4. **Experiments on findings**: every testable high or medium finding becomes an
   experiment (a scenario, an arm, a metric or a judge check) with the refuting
   result stated in advance. Untestable findings are decided by judgement, with
   the reason recorded.
5. **Revise** the change if a finding holds, and return to step 2.
6. **Confirmation**: rerun on the exact text that will ship.
7. **Ship** with the evidence linked from the change note, and record the
   review, the finding experiments and the confirmation in the results doc.

## 10. Reporting

A results section states: the question, arms (with sources and hashes), subject
and judge models, scenarios, trials, plans graded, stubs excluded, the paired
table with intervals, composites, the decision, the adversarial findings and
what their experiments showed, and every deviation from these rules. Commit
verdicts and the harness with the results; never commit private fixtures.

## 11. Cost, throughput and process hygiene

Runs use worker pools (defaults: 8 subject, 10 judge). Parallel calls share the
account's rate limits, so more workers stop helping past a point; watch
progress rather than adding pools. A hung call times out rather than stalling
the pool. Budget grading time for slower models (Grok at medium effort took
about 6.5 minutes per rubric grade).

Long rounds run as background loops, which outlive the command that started
them:
- **Name every model explicitly** in every `run` and `judge` command, even when
  it equals the default. A loop that relies on the default changes behaviour
  when the default changes.
- **Run one grading loop per round.** Before starting another, list the running
  processes and stop the old loop.
- **Verify stops from the process list**, not from the kill command: a pattern
  that does not match leaves the loop running. After stopping, confirm no
  `rubric-eval run`/`judge` process or model call for that round remains.
- A round's verdict count only means something with one judge; if mixed judges
  are found, remove the verdicts written after the change and re-grade them.

## 12. Open items

- Human calibration: 30–50 human-labelled criterion grades, Cohen's kappa per
  criterion group (at least 0.6 for guardrail groups); criteria with low kappa
  get better anchors.
- Judge v3 (quote verification), above.
- Reproduce shipped results on the Grok subject (adversarial review F5): a
  change shipped on Sonnet evidence is not assumed to hold on Grok.
- Review grading reads only the `## Revised plan` section (F6); `diffcheck`
  compares whole plans, and reviewers are not adversarial, so this is accepted
  for now and recorded.
