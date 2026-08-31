---
name: shiploop
description: >-
  Session harness: spec once, walk ready steps via /goal in per-step
  worktrees, close each increment with /shiploop complete.
model: inherit
---

# shiploop

Load and follow the **shiploop** skill (`skills/shiploop/SKILL.md` or the
installed `shiploop` skill). Do not re-author the session procedure here.

- Start / resume: skill card, then follow the packet.
- Reprint: `/shiploop next`.
- Closer: `/shiploop complete` (leftover commit if needed, harness merge, then next packet).
- After every packet, echo `## You are here` and Diagnosis now/pending.
