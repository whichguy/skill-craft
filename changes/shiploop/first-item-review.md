---
bump: minor
---
- **Fewer per-item reviews:** Improve reviews `step-plan` and `test-spec` only for the first work item, and for an item
  that was sent back, whose redone plan is reviewed. Later items follow the pattern the first review set. Every
  implement step, the planning stages, the last carry-forward, `system-test-author` and `release-plan` are reviewed as
  before.

  Why: in a live four-item run, Improve took 99 of 236 minutes. The step plan's review alone took 5 to 14 minutes on
  every item.
