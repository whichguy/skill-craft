---
name: shiploop
description: >-
  Session harness (not DevLoop): spec once, walk ready steps via /goal in
  per-step worktrees, close each increment with /shiploop complete.
model: inherit
---

# shiploop

Load and follow the **shiploop** skill (`skills/shiploop/SKILL.md` or the
installed `shiploop` skill). Do not re-author the session procedure here.

- Start / resume: skill card, then follow the packet.
- Reprint: `/shiploop next`.
- Closer: `/shiploop complete` (commit + merge, then next packet).
- Never invoke `/devloop`.
