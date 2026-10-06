---
bump: minor
---
New run option `--planning-review stage` at `init` and `workspace start`, recorded as `planning_review` in `state.md` like `--backchain-passes` (default `stage`). `stage` is the only value accepted: it starts an Improve child after each of the five planning results, as every run did before, and no packet changes. A retry of `init` or `workspace start` cannot change the option and no verb changes it mid-run. A saved run without the key is refused with the fresh-run hint: start the request again in a fresh `--run-dir` or `--workspace-root`. `graph-dry-run` takes the same flag.
