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

- Native procedure, plan contract and invariants: the skill card.
- Prompts: `prompts/` under the skill package; the run's checks and records:
  `scripts/backchain.py` (`prepare`, `freeze`, `record`, `verify`, `finish`, `check`, `export`).
- Install: the `skill-craft` plugin from your host's marketplace (`skill-craft@whichguy`;
  invoke `/skill-craft:backchain`). OpenCode: `./install.sh --skill backchain` from a Skill
  Craft checkout.
