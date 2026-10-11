---
version: 0.1.0
---
Remove integrated worker worktrees after successful combined delivery and
checks, using Ask Agent's acceptance-bound close. Preserve branches, commits
and durable evidence; report cleanup refusals separately from integration.
Keep failed, unmerged, return-only and ephemeral worktrees. Resume interrupted
cleanup without repeating integration or sweeping historical runs.
