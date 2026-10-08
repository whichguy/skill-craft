---
bump: patch
---
`review-return` now refuses an absolute, `..` or empty `--keep`/`--exclude` path the way it refuses an unknown one, with the undecided paths and the command, and its rule says the paths are relative to the execution checkout. The rollback recipe for a fast-forward with later commits says it also undoes what those commits changed, and points to the diff recipe for keeping their work.
