---
bump: patch
---
- The DAG replay's literal Improve schedule follows ShipLoop's rule `first-item`: step-plan and test-spec park for Improve
  only for the run's first work item and for an item that was sent back. The two-item replay has 42 callbacks, not 44.
