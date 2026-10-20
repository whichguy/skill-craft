---
bump: patch
---
- **Per-step revisit:** after a send-back, each redone inline implement step names its own previous result and its
  commit (`git show <sha>`), not the item's last implement result. A step with no earlier result says so, and a new
  step prints nothing.
