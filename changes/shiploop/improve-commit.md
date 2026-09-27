---
bump: minor
---

New `improve-commit` command for the inline Improve route: the parent writes the
review's commit message to `commit-message.md` beside the receipt with a file
tool, and ShipLoop stages and commits exactly the files the review changed and
has not committed (earlier uncommitted work is left alone). Inline Improve
packets print the command.
