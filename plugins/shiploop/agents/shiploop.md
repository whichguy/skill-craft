---
name: shiploop
description: >-
  Session harness: spec once, walk ready steps via parent until-loop in
  per-step worktrees, close each increment with /shiploop complete.
model: inherit
---

# shiploop

Load and follow the **shiploop** skill (`skills/shiploop/SKILL.md` or the
installed `shiploop` skill). Do not re-author the session procedure here.

- Start / resume: skill card, then Host loop.
- Reprint: `/shiploop next`.
- Closer: `/shiploop complete` execs the printed When done (leftover commit if When done is the merge); the new stdout is the next prompt to issue.
- After every stdout: SKILL.md Host loop (issue this prompt; satisfy any printed precondition; exec When done exactly).
