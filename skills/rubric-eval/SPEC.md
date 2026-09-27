# rubric-eval specification

The reference for how prompt changes are evaluated in this repository. Check it
before running an experiment; change it when the process changes. The
architecture-rubric results that shaped it are in
`docs/shiploop-architecture-rubric-results-2026-09-26.md`.

## 1. Purpose

Decide, with evidence, whether a change to a prompt (a packet block, a review
focus, a platform card, a judge) makes a model's output better, without
regressing what the rubric guards. It answers one question per experiment: is
arm B better than arm A on the same scenarios, under the same condition? Three
things decide it, in strict priority order:

1. **Quality**: comprehensive value against the rubric.
2. **Tokens**: the fewest tokens used (prompt and output, including reasoning).
3. **Time**: the least wall-clock time consumed.

A material quality difference trumps everything. Only when quality is
near-identical (the difference lies within what the judge can tell apart) are
tokens, and then time, consulted.
Every measure and threshold is a standard one, or a quantity measured for this
judge; none is picked by hand (sections 7 and 8).

It does not replace `compare-prompts` (a quick pairwise check of two prompts on
a folder of inputs) or `adversarial-review` (which finds what an experiment
should test). It composes with both.

## 2. Composable parts

Each step is a separate command with a file contract, so any step can be run,
rerun or replaced on its own, and other skills can call it.

| Step | Command | Reads | Writes |
| --- | --- | --- | --- |
| Model call | `call --model grok\|opus\|sonnet` | prompt on stdin | text on stdout (the library's `call_full` also returns tokens and seconds) |
| Exact text | `extract SOURCE [--symbol NAME]` | a source file | the text, and its hash on stderr |
| Build | `build RUN --arm NAME=PATH[::SYMBOL] ...` | a suite, arm texts | `RUN/prompts/*.txt`, `RUN/manifest.json` |
| Run | `run RUN --model M` | prompts | `RUN/out/*.json` (text, tokens, seconds, attempts), `RUN/stubs.log` |
| Judge | `judge RUN --model M` | outputs | `RUN/judge/*.json`, `RUN/judge/failures.log` |
| Analyze | `analyze RUN --baseline ARM` | verdicts | `RUN/analysis.json` |
| Reliability | `reliability RUN --model M --n 30` | verdicts | `RUN/judge_regrade/*.json`, kappa and noise |
| Quote check | `recheck RUN [--judge-dir D]` | verdicts, outputs | `RUN/<D>_qc/*.json` |

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
- no tools beyond what the condition names, **verified** by asking the subject
  to list its tools, never assumed from a flag. Grok reads `--tools ""` as no
  restriction: every Grok call had its shell and file tools until 2026-09-27,
  when it was found (no decision-making result was run on Grok before then).
  `call` now names an allowlist (`todo_write`, or `list_dir` for `--tools Read`)
  and removes the tool-loading meta-tools. Verified live: no shell, no file
  contents (not even its own prompt), and no todo state carried from one call
  to the next. Known limit: in `--tools Read` mode `list_dir` can list other
  directories by name, never their contents;
- a **workspace** run (`run --tools Read --workspace DIR`) gives the subject its
  own copy of reference files (for ShipLoop, `skills/shiploop/references` at a
  pinned commit) and read-only tools: Grok gets `read_file`, `list_dir` and
  `grep`, never a shell or auto-approval, with the prompt passed inline so no
  prompt file is on disk. Grok's kernel sandbox cannot start on a Mac whose
  `/var/run/docker.sock` is a symlink, so every path a call touched is audited
  from its session log. A call that touched anything outside its own directory
  is discarded, rerun and logged to `isolation.log`. The manifest records the
  workspace's file count and hash in the condition. Frames `plan-ref` and
  `review-ref` tell the subject where the references are;
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
times and logs a final failure.

**Judge reliability** is measured by test-retest: the same judge re-grades at
least 30 plans (`reliability`). Two standard figures come out:
- **Cohen's kappa**, linear-weighted over the ordinal grades (missed <
  partial < met), read on the Landis and Koch (1977) bands. A judge is accepted
  at **substantial** (above 0.60) or better.
- **Noise**: the mean absolute change in a plan's score between the two
  gradings, in points. It is the smallest difference this judge can tell apart,
  and `analyze` uses it as the equivalence bound (section 8).

Both go in `references/judges.json`. A judge (a new model or a new judge
prompt) is also accepted only if the decisions of the last completed comparison
do not change when that judge re-grades it.

| Judge (prompt v2) | Kappa | Band | Noise | Measured |
| --- | --- | --- | --- | --- |
| Opus 5.5, medium | 0.835 | almost perfect | 2.07 points | 30 round-4 reviews |
| Sonnet | 0.759 | substantial | 1.69 points | 30 round-3 plans |
| Opus vs Sonnet | 0.443 | moderate | 7.3 points apart | same 30 round-4 reviews |

The last row is why a round never mixes judges: each judge agrees with itself
far better than with the other.

The decisions-unchanged condition is for a new judge prompt meant to grade like
the old one. A change of judge model is the owner's decision (section 6); its
changed decisions are recorded, not hidden. Round 4 under Opus kept prune3's win
and current's loss. design v2 flipped from win to blocked: platform errors
rose, +0.20 per plan, 95% [+0.01, +0.40], with the same quality verdict under
both judges.

**Quote check** (from 2026-09-27). The judge quotes before it grades. `judge`
checks every met or partial grade's quote against the plan, with case and every
non-alphanumeric character normalised; a quote shortened with "..." must match
fragment by fragment. A grade whose quote the plan does not contain drops one
level (met to partial, partial to missed); the verdict records the lowered
criteria in `quote_check` and the judge's own grade as `judge_grade`. `recheck`
applies the check to verdicts graded before it existed; `analyze` refuses a
round that mixes checked and unchecked verdicts; `reliability` checks both sides
before comparing them.

Measured on round 4: the check lowers 17 of Sonnet's and 11 of Opus's grades
across 416 verdicts each, and no decision changes. Both judges quote
accurately. An earlier matcher that normalised only whitespace and markdown
flagged 5.2% of grades, mostly for apostrophes, dashes and commas, and wrongly
cut prune3's lead to +2.7 points (adversarial review F4). Known limit: short
ellipsis fragments can match by coincidence; it is recorded, not guarded.

The judge is shown the expected tier and overbuild note by design, because
proportion cannot be graded without them.

## 8. Statistics and the decision rule

**Scale.** Each criterion is graded on a three-level analytic rubric scored in
points: met 2, partial 1, missed 0 (overbuilt also 0, and counted separately).
A plan's score is the **percentage of available rubric points** it earned,
0–100, over its applicable criteria; `na` criteria are left out. Composites
(rubric groups) are the same percentage over the group's criteria.

**Paired comparison.** Arms are compared **paired** on the same
scenario-runtime-trial cells, by the mean difference in points with:
- a 95% percentile-bootstrap interval (4,000 resamples) that resamples whole
  scenarios by default (`--cluster scenario`), so repeated trials and runtimes
  of one scenario are not counted as independent;
- the **Wilcoxon signed-rank test** (two-sided, normal approximation,
  tie-corrected) over per-scenario mean differences, the independent units;
- cells won and lost.

Token use (prompt plus output tokens, reasoning included, as each CLI reports
them) and wall-clock seconds are compared the same way, per output. When the
baseline is an input that costs nothing this round (the unreviewed plan in a
review experiment), its cost counts as zero. Stub reruns count toward an
output's cost, because they are real cost.

**Significant** means both tests agree on a direction: the 95% interval
excludes zero on that side, and the Wilcoxon test over scenario means rejects
(p < 0.05) with the scenario mean on the same side. A percentile bootstrap over
few clusters runs narrow on its own.

**Decision.** `analyze` returns `winner` (`arm`, `baseline` or none),
`decided_by` and every reason:
1. **Near-identical first.** When the whole overall interval lies within ± the
   judge's measured noise (section 7), quality is near-identical and does not
   decide, even if the difference is significant: a difference smaller than
   the judge's own test-retest change is not material.
   - **Tokens:** the side that significantly uses fewer tokens wins.
   - **Time**, when tokens show no significant difference: likewise for seconds.
   - A tie at every level keeps the baseline; a change must earn its place.
2. **Otherwise, a material quality difference trumps everything.** The arm is
   better when the overall difference is significantly above zero, worse when
   it is significantly below.
3. Anything else is **inconclusive**: add scenarios or trials; no decision.

**Blocking checks.** The arm cannot win at any level while any of these holds,
and a blocked decision lists the blocks first. A win needs both tests; a harm
blocks on the interval alone. That asymmetry is deliberate: shipping needs
strong evidence, and a warning is enough to stop it.
- a guardrail group (`guardrails` in the rubric; for architecture:
  proportion and safeguards) has no comparison, its interval lies wholly below
  zero, or its mean is worse than the judge's noise;
- overbuilt-scope grades or platform errors per plan rose (the paired interval
  lies above zero);
- stub or `na` rates differ between arms, compared paired per output (the
  interval excludes zero), not as independent grades;
- fewer than 8 scenarios were compared (a cluster bootstrap over fewer is
  unreliable);
- the judge has no measured noise, or verdicts come from more than one judge;
- the run's manifest does not record one condition (model, tools) for every arm
  run this round, or an arm other than the baseline is an input.

Cost comparisons name their counts `arm_higher` and `arm_lower`, not won and
lost, because for tokens and seconds the higher side is the worse one. Outputs
whose CLI reported no usage have no token count and are left out; they never
count as zero.

**Shipping** needs, in addition, the adversarial-review loop (section 9) and a
**fresh** confirmation run on the text as it will ship in which the arm wins.
Revising and retesting until something clears is a search, so the result that
ships is the fresh confirmation, never the run that selected it. Under shuffled
labels (no true effect) on round-3 data, the earlier interval-only rule falsely
shipped 3.3% of the time; the rank-test agreement makes the current rule
stricter.

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
- **Keep every long job visible.** Start it as a tracked background task (or
  attach a tracked watcher that ends when its process ends), never only as a
  detached process: the owner must be able to see what is running, and the
  finish is the signal to report, not a timer.
- **Run one grading loop per round.** Before starting another, list the running
  processes and stop the old loop.
- **Verify stops by process ID**, not from the kill command or a text search:
  a kill pattern that does not match leaves the loop running, and a search for
  the loop's text can match the searching shell itself. Record each loop's PID
  when starting it, stop it by PID (with its children), and confirm those PIDs
  are gone; then list `rubric-eval run`/`judge` processes and account for each
  one before starting another.
- A round's verdict count only means something with one judge; if mixed judges
  are found, remove the verdicts written after the change and re-grade them.

## 12. Open items

- Human calibration: 30–50 human-labelled criterion grades, Cohen's kappa per
  criterion group against the judge (substantial or better for guardrail
  groups); criteria with lower kappa get better anchors.
- Rounds 1–5 predate token and time recording; their decisions rest on quality
  alone.
- Reproduce shipped results on the Grok subject (adversarial review F5): a
  change shipped on Sonnet evidence is not assumed to hold on Grok.
- Review grading reads only the `## Revised plan` section (F6); `diffcheck`
  compares whole plans, and reviewers are not adversarial, so this is accepted
  for now and recorded.
