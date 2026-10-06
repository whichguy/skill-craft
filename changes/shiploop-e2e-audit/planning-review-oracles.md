---
bump: minor
---
The DAG replay and the workflow review read ShipLoop's new run option `planning_review` (`stage` or `none`). Every replay case now declares it (a case without one is refused) and the oracle keeps one literal Improve schedule per value, so a `none` run's five planning producers must advance with no child while `system-test-author`, `release-plan` and the last `carry-forward` still park; `synthetic-none-full` replays one. The workflow review judges a run's Improve inventory against the schedule of the mode its state records, and reports a state that records no `planning_review` as unverified instead of comparable (a state that records `none` is judged against the `none` schedule and is comparable).
