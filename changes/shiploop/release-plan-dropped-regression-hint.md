---
bump: patch
---
Surface earlier items' regression commands dropped from the last item's `step-plan` inside `release-plan` packets so `release-plan` can include still-valid suites in `consumer_checks` or note why they were superseded while preserving `release_commands(..., last_item=True)`.
