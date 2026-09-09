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

- Start / resume: skill card, then follow the packet.
- Reprint: `/shiploop next`.
- Closer: `/shiploop complete` reports this prompt's result (leftover commit if When done is the merge), then the script prints the next packet.
- After every packet, echo `## You are here` and Diagnosis now/pending.
