---
bump: minor
---
Research and plan results now carry an `assumptions` list, and the navigator
enforces it. A done research or plan result submitted through `complete` or
`improve-complete` is refused unless every load-bearing assumption is listed as
evidenced, probed or open. Every local evidence path must exist, and a probed
entry must cite a nonempty saved output file. The plan must keep every research
ID and route each open entry to a work item in its queue. The model still
decides whether to experiment; the gate makes a decision not to probe visible.
Runs started before this change are unaffected until their next research or
plan submission, which must include the list.
