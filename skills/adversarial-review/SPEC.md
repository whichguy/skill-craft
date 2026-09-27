# adversarial-review specification

## Purpose

Find, before a change ships, how it could make things worse or how its
evidence could be wrong, as claims an experiment can refute. It is step 3 of
the change lifecycle in `rubric-eval`'s SPEC.

## Inputs

- `change`: the exact before and after text and where it ships. Extract it from
  source; do not paraphrase.
- `evidence`: the results the change rests on, with arms, subject and judge
  models, scenarios, trials and conditions.
- `reviewer`: a model family independent of the proposer (the session model and
  the experiment's subject); `grok` by default, `sonnet` when the proposer is
  Grok.

## Output contract

`findings.json` matching `references/findings.schema.json`:
`{change, reviewer, findings: [{id, claim, severity, category, evidence,
testable, experiment: {type, description, success}}]}`. Categories:
regression, overreach, untested-case, measurement, wording, scope. Experiment
types map to `rubric-eval` actions: `scenario` (add to the suite), `arm` (a
variant of the change), `metric` (an analysis or criterion), `judge` (a judge
check). `success` states the observable result that would refute the claim,
decided before running. `findings.md` renders the same content.

## Rules

- The reviewer is told to find harm, not to praise or rewrite, and to return at
  most N findings, strongest first; an empty list is valid.
- Output that does not validate is retried, then the review fails loudly.
- Every testable high or medium finding gets an experiment; low findings and
  untestable ones are decided by judgement and recorded with the reason.
- Results of finding experiments are recorded next to the change's evidence;
  the review itself is not proof either way.
