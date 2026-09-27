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
`str.format`. The first suite is `suites/architecture`.

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
comparison is void:

- the same frame, scenarios, runtimes, trials, subject model and judge;
- the baseline rerun in the same round, not reused from another condition;
- no MCP servers or plugins in any headless call (`call` enforces this);
- a control cannot read the treatment (no shared readable directory);
- stubs (graded text under 150 words) rerun with the same prompt up to three
  times, then excluded and logged, never graded as failures;
- the judge sees one output at a time, never the arm name.

## 6. Models

- **Subject** (the model the prompt runs on): `sonnet`, or `grok` (grok-4.7 at
  medium effort, ShipLoop's real host). Name it in every result. A result on
  one subject is not assumed to hold on the other.
- **Judge**: `sonnet` with the evidence-first prompt (section 7).
- **Adversarial reviewer**: a model family other than the one that proposed the
  change (see the `adversarial-review` skill).
- Never Haiku.

## 7. Judge

Evidence first: for each applicable criterion, quote the shortest exact span of
the plan that decides it, then grade from that quote (`met`, `partial`,
`missed`, `overbuilt`, `na`), with grade anchors in the prompt and the criteria
stated before and after the plan. Each call times out, retries up to three
times and logs a final failure. A new judge version must be re-graded on at
least 30 plans before use; accept it if the mean per-plan score change is 0.03
or less (judge v2: 0.017; v1: 0.041).

## 8. Statistics and the ship rule

Scores: met 1, partial 0.5, missed and overbuilt 0, averaged over graded
criteria. Compare arms **paired** on the same scenario-runtime-trial cells:
mean difference, a 95% bootstrap interval (4,000 resamples), and cells won and
lost. Report composites for every group in the suite.

A change **ships** only when:
1. the overall 95% interval against the baseline lies above zero, and
2. no guardrail group (`guardrails` in the rubric; for architecture:
   proportion and safeguards) has an interval wholly below −0.02, and
3. the adversarial-review loop (section 9) is complete, and
4. a confirmation run on the text as it will ship reproduces condition 1.

`analyze` applies rules 1 and 2 and reports them as `decision`.

## 9. Change lifecycle

1. **Hypothesis**: what the change should improve, and what it might harm.
2. **Experiment**: arms extracted from source; build, run, judge, analyze.
3. **Adversarial review** of the proposed change and its evidence
   (`adversarial-review review`), by a different model family.
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

## 11. Cost and throughput

Runs use worker pools (defaults: 8 subject, 10 judge). Parallel calls share the
account's rate limits, so more workers stop helping past a point; watch
progress rather than adding pools. A hung call times out rather than stalling
the pool.

## 12. Open items

- Human calibration: 30–50 human-labelled criterion grades, Cohen's kappa per
  criterion group; criteria with low kappa get better anchors.
- A second judge family on the lowest-agreement criteria.
