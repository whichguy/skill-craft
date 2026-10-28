# shiploop-run

Grades the prose a ShipLoop run produces where a lower reasoning effort could degrade it without a script
noticing: the accepted results of `system-test`, `product-acceptance`, `release-verify` and `operations`, and
Improve review notes `review-<n>.md` for pass n >= 2. Built for the by-stage effort experiment
(`docs/shiploop-effort-by-stage-experiment-plan-2026-10-24.md`, R0.5 and Q2).

Each artifact is graded against its own **run record** (the facts block): what ShipLoop's scripts recorded
(reruns of the stage's recorded commands with exits, ids and output tails; Improve pass records with label,
tree change and commit; the repository's commits with times and files) and the earlier accepted results that
state.md holds. Four criteria (`rubric.json`), each with met 2 / partial 1 / missed 0 anchors and an N/A rule:

| Id | Criterion | Group |
| --- | --- | --- |
| F1 | Recorded facts: statements agree with the run record where it covers them | truth (guardrail) |
| F2 | Required fields: every item the artifact's kind must report (listed in `judge.txt`) | completeness |
| F3 | Fresh evidence: relied-on results postdate the last product edit | freshness |
| F4 | Supported claims: success claims are backed and in proportion | truth (guardrail) |

Score: percent of rubric points per artifact, as for every suite. `platform_errors` in a verdict lists artifact
statements the run record contradicts, so `analyze` blocks an arm whose contradictions rise.

## Files

- `rubric.json`, `scenarios.json`: the criteria and one scenario per E2E case (`test/shiploop_e2e/cases.json`);
  `decision_round` marks the eight cases of the effort experiment. The case note (`overbuild`) says which checks
  are real for that case. A scenario's slots (runtimes) are the four stage kinds and `review-<stage>`.
- `judge.txt`: this suite's judge template (`rubric_eval.load_suite` reads it). It states the criteria before
  and after the artifact and gives the run record in its own fence; the judge quotes the artifact as
  `evidence` and the record as `fact`, and both quotes are checked (`verify_quotes`).
- `import_run.py`: the import path. Outputs come from ShipLoop runs, not from `rubric-eval run`:

```sh
S=skills/rubric-eval
python3 -B $S/suites/shiploop-run/import_run.py collect RUNROOT... --out pool.jsonl
python3 -B $S/suites/shiploop-run/import_run.py place RUN --pool pool.jsonl --arm control \
    --condition grok:grok-4.7@medium [--select ids.txt] [--tokens usage.json]
python3 -B $S/scripts/rubric-eval judge RUN --suite shiploop-run --model opus --dest judge_p1
python3 -B $S/scripts/rubric-eval reliability RUN --suite shiploop-run --model opus --n 30
python3 -B $S/scripts/rubric-eval analyze RUN --suite shiploop-run --baseline control --judge-dir judge_p1,judge_p2,judge_p3
```

`place` writes `RUN/manifest.json` with one recorded condition and `"min_words": 1` (an imported artifact is
real at any length, never a stub), and `RUN/out/<case>_<slot>_<arm>_<trial>.json` with `text`, `facts`,
`input_tokens`, `output_tokens` (None unless `--tokens` supplies them; None is left out, never zero) and
`seconds` (the stage's or pass's span from the run's own times). It refuses a second condition in one RUN.
Neither the text nor the facts carry the host, model, effort or arm: the judge never sees the condition.
Paths under the run folder are shortened to `run/`, `worktree/`; addresses and anything token-like are
scrubbed. The text is the accepted result's fields rendered in a fixed order with their values verbatim.

## Known limits

- Pairing across arms is by order within a case and slot (`trial` = the n-th artifact of that slot), so two
  arms with different numbers of Improve passes pair only their common prefix; unpaired cells are dropped by
  `analyze`. Per-scenario means are what the decision uses.
- Improve reviews are graded only where ShipLoop wrote per-pass records (`reviews/pass-<n>.json`, runs from
  2026-10-17 on); older runs have no script record of a pass's label or tree change.
- The run record cannot cover command output the model captured itself (`run/scratch/*`); such claims are
  judged under F4 by what the artifact cites.

Acceptance (SPEC section 7) is recorded in `references/judges.json` (`opus_shiploop_run`) and the evidence in
`docs/experiments/shiploop-effort-by-stage-20261024/judge/`.
