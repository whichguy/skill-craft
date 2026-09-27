---
bump: minor
---

ShipLoop commits a work item's changes itself when `integrate` is accepted: the
files the item changed that its step plan's `paths` declare, plus
`docs/shiploop/`, with the item title and integrate summary as the message
(the configured identity, else the workspace identity). It prints the commit
and names every other changed file for the model to commit or delete. The
model no longer writes the item commit, which headless hosts refused, and a
run no longer ends with its product uncommitted in the execution worktree.
