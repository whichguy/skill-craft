---
bump: minor
---
The final report lists what the run left in your repository — merged attempt branches, kept (rejected or lost) attempt worktrees, and the run's own branch and workspace — with the command to remove each, and the completion packet says how many there are. ShipLoop still never deletes them itself. Commands use `git branch -d` wherever the branch is merged (it refuses to lose work) and never `--force`; nothing is offered for removal before the run is returned.
