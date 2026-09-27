---
name: rubric-eval
description: >-
  Evaluate a prompt change against a rubric over a scenario catalog: run arms on
  a subject model (Sonnet or Grok), grade blind with an evidence-first judge, and
  decide with paired bootstrap intervals and guardrails. Use when deciding
  whether to ship a change to a packet block, review focus, platform card or
  judge; for "run the rubric", "rubric eval", "A/B this wording across the
  scenarios", or confirming a change on the text that ships. For a quick
  pairwise check of two prompts on a folder of inputs, use compare-prompts.
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
---

# rubric-eval

Read [SPEC.md](SPEC.md) before an experiment; it is the reference for the
condition rules, models, judge, statistics, ship rule and change lifecycle.
This page is how to drive it.

The CLI is `scripts/rubric-eval` (Python 3, no dependencies). Each subcommand is
one step with a file contract, so other skills can call any step:

```sh
E=scripts/rubric-eval
$E extract skills/shiploop/scripts/shiploop_navigator_v3_prompts.py --symbol INTERACTION_DESIGN
$E build RUN --arm base=OLD.py::INTERACTION_DESIGN --arm cand=NEW.py::INTERACTION_DESIGN --trials 2
$E run RUN --model sonnet          # or --model grok (grok-4.7, medium effort)
$E judge RUN
$E analyze RUN --baseline base      # composites, paired intervals, decision
$E reliability RUN --n 30           # when the judge changes
echo "prompt" | $E call --model grok
```

Review experiments grade a review's revised plan: build with `--frame review
--plans-from PLAN_RUN --plans-arm ARM` and one `--arm` per review focus.

## Workflow for a change

1. State the hypothesis and what the change might harm.
2. Extract arms from source (never retype them), then build, run, judge and
   analyze. Keep every arm under one condition (SPEC section 5).
3. Run `adversarial-review` on the change and its evidence, with a model family
   other than the one proposing it.
4. Turn each testable high or medium finding into an experiment with its
   refuting result stated first; run it; revise the change if a finding holds.
5. Rerun on the exact text that will ship. Ship only when `analyze` says
   `ship: true` there and the loop is complete (SPEC section 8).
6. Record everything in the results doc (SPEC section 10).

Long runs: report progress at the interval the user asks for, with interim
paired results; they stabilise as more cells finish.
