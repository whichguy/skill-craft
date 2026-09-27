---
name: adversarial-review
description: >-
  Have an independent model try to break a proposed change and return its
  findings as testable hypotheses, each with the smallest experiment that would
  refute it. Use before shipping any prompt, review-focus, card or harness
  change decided from experiments; for "adversarial review", "red-team this
  change", "what could this break". Writes findings.json for rubric-eval.
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
---

# adversarial-review

Read [SPEC.md](SPEC.md) for the findings contract and how findings become
experiments. It composes the `rubric-eval` skill's model call, so install both.

```sh
A=scripts/adversarial-review
$A review --name "prune review" --change change.md --evidence evidence.md --out RUN/adversarial --reviewer grok
$A validate RUN/adversarial/findings.json
```

- `change.md`: the exact text before and after, and where it ships.
- `evidence.md`: the experiment results the change rests on (tables, arms,
  subject and judge models, conditions).
- `--reviewer`: a model family other than the one that proposed or produced the
  change; default `grok`.

Then, for each testable high or medium finding, run its experiment with
`rubric-eval` and record whether the stated refuting result occurred. A finding
that holds sends the change back for revision; one that is refuted is recorded
with its evidence. Findings marked not testable are decided by judgement, with
the reason written down.
