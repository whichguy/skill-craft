---
bump: patch
---
A session that cannot read the process table no longer takes over a live session's run.
- When `ps` is missing, times out or is hidden by a sandbox, the keepalive treated every recorded owner as gone and let a
  second session claim the run at once, so two sessions could drive one run. An unreadable table now counts as unknown,
  and only the 30-minute rule frees the claim.
- The owner's own hook in that situation keeps the process it recorded instead of overwriting it with none.
