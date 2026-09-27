---
bump: minor
---
New explicit route `workspace_route: current` ("in place", `--in-place`, "just use the current worktree"): a fresh worker runs in the caller's own checkout and branch, with no helper worktree, receipt or close. It defaults to `report-only`; `in-place` writes need a declared write set. The helper's new read-only `current-state` command records a baseline and reports `unchanged`, `changed-within-write-set` or `drift`. An explicitly requested cheaper model or read-only agent type is honored and disclosed. Plan Dispatcher, ShipLoop and improve-agent keep the helper-managed route.
