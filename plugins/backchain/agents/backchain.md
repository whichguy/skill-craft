---
name: backchain
description: >-
  Use when an implementation task needs a dependency-aware plan before coding:
  backward planner / backchain / precondition-first planning, dependency DAGs,
  elaborating incomplete plans, or scheduler-ready step graphs.
model: inherit
---

# backchain

Load and follow the **backchain** skill (`skills/backchain/SKILL.md` or the installed
`backchain` skill). Do not re-author the full planning procedure here.

- Mode table, native procedure, harness packaging, and plan contract: skill card.
- Prompts: `prompts/` under the skill package (generator, elaborator, dependency-review).
- Install: use your host's plugin marketplace (`backchain` plugin), or from a Backchain
  source checkout run `./install.sh --skill backchain` (optional `--agents` for this card).
