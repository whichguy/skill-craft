---
bump: minor
---
- The export and the page use ShipLoop's four outcomes. A historical run's `revise` and `replan` read as `send-back` and
  `add-work`.
- A work item's `revises` count is now `sendBacks`. Its implement-visit counts are done, send-back, add-work and blocked,
  plus repeat for historical runs.
- A corrective item's `origin` is `add-work`.
- A blocked run's "by" shows what it awaits.
