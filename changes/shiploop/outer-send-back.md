---
bump: minor
---
- **Send-back at the release stages:**
  - `system-test` may send the run back to `system-test-author` when a case or command in its test plan is wrong;
  - `release-verify` may send it back to `release-plan` when the release plan or one of its consumer checks is wrong.

  The target reruns with the result as evidence. Its packet names the result that sent it back and its own previous
  result, and asks for an amendment. Every stage after the target then runs again.
- **Budget:** each target has its own budget of two send-backs, checked at `--check-only` as for a work item. After that
  the stage reports blocked, awaiting a decision.
- **Repeated refused runs** at those two stages still end in `add-work`: a refused run shows the product failing, not
  the plan.
- **No repeated release:** after a send-back from `release-verify`, `release` runs only what the amended plan changed.
  An unchanged operation keeps its earlier receipt and does not run twice.
