---
bump: minor
---
- **An item brings its own tests:** a done step plan is refused when a focused command lists only test IDs that an
  earlier work item's step plan already made focused. That command is the earlier item's regression. A new focused ID
  beside old ones passes.
- **A printed path is not a load failure:** the base run no longer reads a line that is only a file path as a load
  failure of an added file, so a `printf <new file> && test -f <new file>` guard no longer fakes RED. The base rule
  and the not-run refusal ask for a failure caused by the missing behaviour.
